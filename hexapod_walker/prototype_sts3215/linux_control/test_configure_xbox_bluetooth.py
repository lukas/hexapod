"""BlueZ repair mechanics use disposable files, never real adapter keys/services."""
import os
from pathlib import Path
import re
import stat
from types import SimpleNamespace

import pytest

import configure_xbox_bluetooth as setup

MAC = "14:B5:CD:E8:70:07"


@pytest.fixture
def files(tmp_path):
    config = tmp_path / "main.conf"
    config.write_text("# keep my comments\n[General]\nName = my robot\nPrivacy = off # explain\n[Policy]\nAutoEnable = true\n")
    config.chmod(0o644)
    storage = tmp_path / "bluetooth"
    adapter = storage / MAC
    adapter.mkdir(parents=True)
    return config, storage, adapter / "identity"


def test_config_edits_preserve_comments_unknown_settings_and_are_idempotent():
    original = "# heading\n[General]\nName = custom\nPrivacy = off # why\nJustWorksRepairing=never\n[LE]\n# user choice\nMinConnectionInterval=10\n[Policy]\nAutoEnable=true\n"
    result = setup.update_config(original)
    assert "# heading\n[General]\nName = custom\n# why\nPrivacy = device\n" in result
    assert "# user choice\nMinConnectionInterval=7\n" in result
    assert "[Policy]\nAutoEnable=true\n" in result
    parsed = setup.parse_config(result)
    for section, values in setup.SETTINGS.items():
        for key, value in values.items():
            assert parsed[section][key] == value
    assert setup.update_config(result) == result


def test_kernel_crypto_independent_identity_and_exact_config_backup(files, capsys):
    config, storage, identity = files
    original = config.read_bytes()
    created, backup = setup.configure_files(MAC.lower(), config=config, storage=storage)
    assert created and backup.read_bytes() == original
    assert stat.S_IMODE(backup.stat().st_mode) == 0o644
    assert stat.S_IMODE(config.stat().st_mode) == 0o644
    assert stat.S_IMODE(identity.stat().st_mode) == 0o600
    assert identity.stat().st_uid == os.geteuid()
    contents = identity.read_text()
    assert re.fullmatch(r"\[General\]\nIdentityResolvingKey=[0-9a-f]{32}\n", contents)
    assert contents not in capsys.readouterr().out
    # No kernel crypto sockets/modules are needed: secrets uses OS entropy.
    assert setup.configure_files(MAC, config=config, storage=storage) == (False, None)
    assert identity.read_text() == contents
    assert len(list(config.parent.glob("main.conf.xbox-backup-*"))) == 1


def test_valid_existing_identity_preserved_byte_for_byte(files):
    config, storage, identity = files
    original = "# identity comment\n[General]\nIdentityResolvingKey=" + "ab" * 16 + "\n"
    identity.write_text(original)
    identity.chmod(0o600)
    inode = identity.stat().st_ino
    assert setup.configure_files(MAC, config=config, storage=storage)[0] is False
    assert identity.read_text() == original and identity.stat().st_ino == inode


@pytest.mark.parametrize("contents", [
    "secret line that must not appear in an error",
    "[General]\nIdentityResolvingKey=private-broken-value\n",
    "[DEFAULT]\nIdentityResolvingKey=" + "ab" * 16 + "\n[General]\n",
    "[General]\nIdentityResolvingKey=" + "ab" * 16 + "\nIdentityResolvingKey=duplicate-secret\n",
])
def test_invalid_identity_refused_without_overwrite_or_leaking_contents(files, contents):
    config, storage, identity = files
    original_config = config.read_bytes()
    identity.write_text(contents)
    identity.chmod(0o600)
    with pytest.raises(ValueError) as error:
        setup.configure_files(MAC, config=config, storage=storage)
    assert "secret" not in str(error.value) and "private-broken-value" not in str(error.value)
    assert identity.read_text() == contents
    assert config.read_bytes() == original_config
    assert not list(config.parent.glob("main.conf.xbox-backup-*"))


def test_refuses_insecure_identity_permissions_and_symlink(files):
    config, storage, identity = files
    identity.write_text("[General]\nIdentityResolvingKey=" + "ab" * 16 + "\n")
    identity.chmod(0o644)
    with pytest.raises(ValueError, match="0600"):
        setup.configure_files(MAC, config=config, storage=storage)
    identity.unlink()
    identity.symlink_to(config)
    with pytest.raises(OSError):
        setup.configure_files(MAC, config=config, storage=storage)


def test_concurrently_created_identity_never_overwritten(files, monkeypatch):
    _config, _storage, identity = files
    original = "[General]\nIdentityResolvingKey=" + "cd" * 16 + "\n"
    def concurrent_link(source, destination):
        Path(destination).write_text(original)
        Path(destination).chmod(0o600)
        raise FileExistsError
    monkeypatch.setattr(setup.os, "link", concurrent_link)
    assert setup.ensure_identity(identity) is False
    assert identity.read_text() == original
    assert not list(identity.parent.glob(".identity-*"))


def test_active_daemon_refused_before_any_write(monkeypatch, capsys):
    monkeypatch.setattr(setup.os, "geteuid", lambda: 0)
    monkeypatch.setattr(setup.subprocess, "run", lambda *args, **kw: SimpleNamespace(stdout="active\n"))
    monkeypatch.setattr(setup, "configure_files", lambda *args, **kw: pytest.fail("wrote while active"))
    with pytest.raises(SystemExit) as error:
        setup.main(["--adapter", MAC])
    assert error.value.code == 1
    assert "Close bluetoothctl" in capsys.readouterr().err


def test_success_always_restarts_after_files_to_reload_autoactivated_daemon(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(setup.os, "geteuid", lambda: 0)
    def run(argv, **kwargs):
        calls.append(argv[1])
        return SimpleNamespace(stdout="inactive\n")
    def configure(*args, **kwargs):
        calls.append("write")
        return True, None
    monkeypatch.setattr(setup.subprocess, "run", run)
    monkeypatch.setattr(setup, "configure_files", configure)
    setup.main(["--adapter", MAC])
    assert calls == ["show", "write", "restart"]
    assert "privacy" in capsys.readouterr().out
