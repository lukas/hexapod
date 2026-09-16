"""W&B's 128-character boundary must not discard retained checkpoints."""

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from rl_move.sim.artifact_names import (
    bounded_artifact_name, checkpoint_artifact_name, publish_checkpoint)


@pytest.mark.parametrize("size", [127, 128, 129])
def test_sdk_name_boundary_and_legacy_identity(size):
    original = "a" * size
    name = bounded_artifact_name(original)
    assert len(name) <= 128
    if size <= 128:
        assert name == original
    else:
        assert name == bounded_artifact_name(original)
        assert name != bounded_artifact_name(original[:-1] + "b")


class Artifact:
    def __init__(self, name, *, type, metadata):
        if len(name) > 128:
            raise ValueError("Artifact name is longer than 128 characters")
        self.name, self.type, self.metadata = name, type, metadata
        self.files = []

    def add_file(self, path, name=None):
        self.files.append((name or Path(path).name, Path(path).read_bytes()))


def test_long_checkpoint_publication_preserves_bytes_and_lineage(tmp_path, monkeypatch):
    run_name = "cw-walkscratch-" + "same-prefix-" * 10 + "guardfix1"
    stem = "ppo_goal_" + run_name.replace("-", "_")
    with pytest.raises(ValueError):
        Artifact("ckpt-" + stem, type="policy-checkpoint", metadata={})
    monkeypatch.setitem(sys.modules, "wandb", SimpleNamespace(Artifact=Artifact))
    checkpoint = tmp_path / (stem + ".zip")
    data = b"retained checkpoint bytes"
    checkpoint.write_bytes(data)
    logged = []
    run = SimpleNamespace(log_artifact=lambda art, aliases: logged.append((art, aliases)))
    art = publish_checkpoint(run, checkpoint, run_name=run_name, steps=2097152,
                             task="joint_walk", parent_ckpt="original_parent")
    assert art.name == checkpoint_artifact_name(stem)  # Consumer's lookup key.
    assert art.files == [(checkpoint.name, data)]
    assert art.metadata["run"] == run_name
    assert art.metadata["original_artifact_name"] == "ckpt-" + stem
    assert art.metadata["parent_ckpt"] == "original_parent"
    assert art.metadata["md5"] == hashlib.md5(data).hexdigest()[:8]
    assert logged[0][1][0] == "latest"
    assert all(len(a) <= 128 for a in logged[0][1])

