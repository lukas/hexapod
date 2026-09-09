"""Docs symlinked from the prototype tree into the state repo must still be
served (status_server /llm/doc, mcp_server read_doc). Regression for the
09-08 move: the traversal guard only accepted paths resolving under PROTO,
so every journal and run story 404'd."""
from __future__ import annotations

import os

import mcp_server
import state_dir
import status_server


def _layout(tmp_path, monkeypatch):
    proto = tmp_path / "proto"
    state = tmp_path / "state"
    (proto / "rl_docs" / "tracks" / "amp").mkdir(parents=True)
    (state / "rl_docs" / "tracks" / "amp").mkdir(parents=True)
    (state / "rl_docs" / "tracks" / "amp" / "STATUS.md").write_text("# amp\nhello\n")
    os.symlink(os.path.relpath(state / "rl_docs" / "tracks" / "amp" / "STATUS.md",
                               proto / "rl_docs" / "tracks" / "amp"),
               proto / "rl_docs" / "tracks" / "amp" / "STATUS.md")
    (tmp_path / "outside.md").write_text("nope\n")
    os.symlink(tmp_path / "outside.md", proto / "escape.md")
    monkeypatch.setattr(state_dir, "STATE_DIR", state)
    monkeypatch.setattr(status_server, "PROTO", proto)
    monkeypatch.setattr(mcp_server, "PROTO", proto)
    return proto


def test_status_server_serves_doc_symlinked_into_state(tmp_path, monkeypatch):
    _layout(tmp_path, monkeypatch)
    assert status_server.llm_doc_file("rl_docs/tracks/amp/STATUS.md") == b"# amp\nhello\n"


def test_status_server_still_refuses_symlink_escaping_both_roots(tmp_path, monkeypatch):
    _layout(tmp_path, monkeypatch)
    assert status_server.llm_doc_file("escape.md") is None
    assert status_server.llm_doc_file("../outside.md") is None


def test_mcp_read_doc_follows_state_symlink(tmp_path, monkeypatch):
    _layout(tmp_path, monkeypatch)
    out = mcp_server._read_doc("rl_docs/tracks/amp/STATUS.md")
    assert "hello" in (out if isinstance(out, str) else str(out))
