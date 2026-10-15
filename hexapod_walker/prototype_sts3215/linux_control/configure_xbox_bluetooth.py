#!/usr/bin/env python3
"""Opt-in BlueZ Xbox BLE bond repair; run as root with Bluetooth stopped.

This changes global BlueZ privacy/LE defaults and restarts Bluetooth. It never
pairs a device, removes a bond, changes robot control, or prints a secret key.
"""
from __future__ import annotations

import argparse
import configparser
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import tempfile

SETTINGS = {
    "General": {"Privacy": "device", "JustWorksRepairing": "confirm"},
    "LE": {"MinConnectionInterval": "7", "MaxConnectionInterval": "9",
           "ConnectionLatency": "0", "ConnectionSupervisionTimeout": "200"},
}
SECTION = re.compile(r"^\s*\[([^]]+)\]\s*(?:[#;].*)?$")
ASSIGNMENT = re.compile(r"^(\s*([^=#;\s]+)\s*=\s*)([^#;]*?)(\s*(?:[#;].*)?)$")


def parse_config(text: str) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(interpolation=None, delimiters=("=",))
    parser.optionxform = str
    try:
        parser.read_string(text)
    except configparser.Error:
        # Parser exceptions include source lines; identity files contain secrets.
        raise ValueError("Invalid configuration format; inspect the file locally before retrying.") from None
    return parser


def update_config(text: str) -> str:
    """Edit only active target assignments; leave comments and other keys intact."""
    parse_config(text)
    missing = {section: dict(values) for section, values in SETTINGS.items()}
    output = []
    section = None

    def append_missing(name):
        if name in missing:
            if output and not output[-1].endswith("\n"):
                output[-1] += "\n"
            output.extend(f"{key} = {value}\n" for key, value in missing.pop(name).items())

    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        header = SECTION.match(body)
        if header:
            append_missing(section)
            section = header[1]
        assignment = ASSIGNMENT.match(body)
        if assignment and section in missing and assignment[2] in missing[section]:
            value = missing[section].pop(assignment[2])
            suffix = assignment[4]
            if suffix.strip():
                # GLib keyfiles require comments on their own line.
                output.append("#" + suffix.lstrip()[1:] + "\n")
                suffix = ""
            line = assignment[1] + value + suffix + line[len(body):]
        output.append(line)
    append_missing(section)
    for name in list(missing):
        if output and not output[-1].endswith("\n"):
            output[-1] += "\n"
        output.append(f"\n[{name}]\n")
        append_missing(name)
    return "".join(output)


def validate_identity(path: Path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise ValueError("Existing identity must be a regular root-owned file with mode 0600; fix ownership/permissions without replacing its key.")
        try:
            parser = parse_config(stream.read().decode("utf-8"))
            key = (parser.get("General", "IdentityResolvingKey", fallback="")
                   if not parser.defaults() else "")
        except (UnicodeDecodeError, configparser.Error, ValueError):
            raise ValueError("Existing BlueZ identity is invalid; refusing to replace it. Inspect it locally without publishing its contents.") from None
    if not re.fullmatch(r"[0-9a-fA-F]{32}", key):
        raise ValueError("Existing BlueZ identity has an invalid IRK; refusing to replace it.")


def ensure_identity(path: Path) -> bool:
    try:
        validate_identity(path)
        return False
    except FileNotFoundError:
        pass
    # BlueZ 5.82 generate_and_write_irk() calls bt_crypto_new() before drawing
    # random bytes. Uno Q kernels without CONFIG_CRYPTO_USER_API_HASH/SKCIPHER
    # fail there even though OS entropy is available. secrets uses that OS
    # entropy directly and writes BlueZ's normal 16-byte adapter IRK format:
    # https://github.com/bluez/bluez/blob/5.82/src/adapter.c#L3948-L4053
    fd, temporary = tempfile.mkstemp(prefix=".identity-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write("[General]\nIdentityResolvingKey=" + secrets.token_hex(16) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)  # Atomic publish, never clobber a concurrent BlueZ key.
        except FileExistsError:
            validate_identity(path)
            return False
        return True
    finally:
        os.unlink(temporary)


def configure_files(adapter: str, *, config: Path, storage: Path) -> tuple[bool, Path | None]:
    if not re.fullmatch(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", adapter):
        raise ValueError("--adapter must be the board's Bluetooth MAC from bluetoothctl list.")
    directory = storage / adapter.upper()
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Adapter storage directory is missing or a symlink; verify the adapter MAC and initialize BlueZ first.")
    if config.is_symlink() or not config.is_file():
        raise ValueError("main.conf must be an existing regular file, not a symlink.")
    original = config.read_bytes()
    updated = update_config(original.decode("utf-8")).encode("utf-8")
    created = ensure_identity(directory / "identity")
    if original == updated:
        return created, None
    metadata = config.stat()
    backup_fd, backup = tempfile.mkstemp(prefix=config.name + ".xbox-backup-", dir=config.parent)
    with os.fdopen(backup_fd, "wb") as stream:
        stream.write(original)
        os.fchmod(stream.fileno(), stat.S_IMODE(metadata.st_mode))
        os.fchown(stream.fileno(), metadata.st_uid, metadata.st_gid)
        stream.flush()
        os.fsync(stream.fileno())
    fd, temporary = tempfile.mkstemp(prefix=".main.conf-", dir=config.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(updated)
            os.fchmod(stream.fileno(), stat.S_IMODE(metadata.st_mode))
            os.fchown(stream.fileno(), metadata.st_uid, metadata.st_gid)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, config)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return created, Path(backup)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", required=True, help="Board adapter MAC from bluetoothctl list")
    args = parser.parse_args(argv)
    if os.geteuid() != 0:
        parser.error("Run with sudo; this explicitly changes BlueZ configuration and restarts Bluetooth.")
    try:
        state = subprocess.run(["systemctl", "show", "bluetooth.service", "--property=ActiveState", "--value"],
                               check=True, capture_output=True, text=True).stdout.strip()
        if state != "inactive":
            raise ValueError("Close bluetoothctl, then run sudo systemctl stop bluetooth.service before this helper.")
        created, backup = configure_files(args.adapter, config=Path("/etc/bluetooth/main.conf"), storage=Path("/var/lib/bluetooth"))
        # A still-open D-Bus client may autoactivate bluetoothd after our stopped
        # check. Always restart after writes so it reads the completed identity.
        subprocess.run(["systemctl", "restart", "bluetooth.service"], check=True)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Bluetooth setup failed: {exc}\n")
    print("BlueZ identity " + ("created securely." if created else "preserved."))
    if backup:
        print(f"Previous main.conf saved to {backup}")
    print("Bluetooth restarted. Check sudo btmgmt info: current settings must include privacy before pairing.")


if __name__ == "__main__":
    main()
