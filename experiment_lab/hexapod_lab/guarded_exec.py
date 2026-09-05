"""Exec a guarded command only after its deadline wrapper authorizes launch."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--go-fd", required=True, type=int)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        parser.error("a command is required")
    try:
        permission = os.read(args.go_fd, 1)
    finally:
        os.close(args.go_fd)
    if permission != b"G":
        return 125
    os.execvpe(command[0], command, os.environ)
    return 126


if __name__ == "__main__":
    raise SystemExit(main())
