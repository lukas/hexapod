import subprocess

from hexapod_lab.engineering_lane import workspace_snapshot, write_workspace_patch


def test_committed_fix_remains_in_attempt_patch(tmp_path):
    def git(*args):
        return subprocess.run(["git", *args], cwd=tmp_path, check=True,
                              text=True, capture_output=True).stdout.strip()

    git("init", "-b", "repair")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Test")
    (tmp_path / "controller.txt").write_text("before\n")
    git("add", "controller.txt")
    git("commit", "-m", "Baseline")
    before = workspace_snapshot(tmp_path)
    (tmp_path / "controller.txt").write_text("fixed\n")
    (tmp_path / "new_regression.txt").write_text("new file included\n")
    git("add", "controller.txt", "new_regression.txt")
    git("commit", "-m", "Fix measured problem")
    after = workspace_snapshot(tmp_path)
    assert after["status"] == ""
    assert before["branch"] == after["branch"] == "repair"
    assert after["upstream"] is None
    assert before["head"] != after["head"]
    receipt = write_workspace_patch(tmp_path, tmp_path / "attempt.patch", 10000,
                                    base_head=before["head"])
    patch = (tmp_path / "attempt.patch").read_text()
    assert "+fixed" in patch and "+new file included" in patch
    assert receipt["base_head"] == before["head"]
    assert receipt["bytes"] > 0
