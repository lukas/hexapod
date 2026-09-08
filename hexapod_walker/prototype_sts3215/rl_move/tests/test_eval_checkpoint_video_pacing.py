"""Video pacing preserves full sequential rollouts and honest encoded timing."""
from __future__ import annotations

import copy
import random

import numpy as np
import pytest


pytest.importorskip("mujoco")
torch = pytest.importorskip("torch")

from rl_move.config import load_config
from rl_move.sim import eval_checkpoint as evaluation
from rl_move.sim.walk_task import SimHexapodJointWalkEnv


class _Model:
    use_sde = True

    def __init__(self):
        self.policy = self
        self.reset_calls = self.noise_calls = self.predict_calls = 0
        self.noise = np.zeros(18)

    def reset(self):
        self.reset_calls += 1

    def reset_noise(self, n_envs=1):
        assert n_envs == 1
        self.noise_calls += 1
        self.noise = torch.randn(18).numpy() * 0.002

    def predict(self, obs, deterministic=True):
        self.predict_calls += 1
        action = np.tanh(np.asarray(obs[:18], dtype=float)) * 0.002
        if not deterministic:
            action += self.noise + torch.randn(18).numpy() * 0.001
            action += np.random.normal(0.0, 0.001, 18)
            action += (random.random() - 0.5) * 0.001
        return action, None


def _env(*, hz=100, seconds=0.24, randomize=False):
    cfg = load_config()
    cfg.setdefault("control", {})["hz"] = hz
    env = SimHexapodJointWalkEnv(
        cfg, seed=0, episode_seconds=max(2.0, seconds), randomize=randomize,
        dr_scale=0.2 if randomize else 0.0)
    for mode in evaluation.ALL_MODES:
        if hasattr(env._goal_gen, f"p_{mode}"):
            setattr(env._goal_gen, f"p_{mode}", float(mode == "walk"))
    # The real walk planner requires its one-second hold to fit. Generate
    # its normal two-second plan, then shorten only the rollout horizon.
    planning_steps = env.episode_steps
    reset = env.reset

    def short_reset(*args, **kwargs):
        env.episode_steps = planning_steps
        result = reset(*args, **kwargs)
        env.episode_steps = int(round(seconds / env.dt))
        return result

    env.reset = short_reset
    return env


def _renderer(env):
    rendered, annotated = [], []

    def render():
        rendered.append(env._step_i)
        return np.full((16, 16, 3), env._step_i, dtype=np.uint8)

    def annotate(frame, lines):
        annotated.append(tuple(lines))
        return frame

    env.render = render
    return rendered, annotated, annotate


def _exact(left, right):
    if isinstance(left, np.ndarray):
        assert left.dtype == right.dtype
        assert left.shape == right.shape
        assert left.tobytes() == right.tobytes()
    elif isinstance(left, torch.Tensor):
        assert torch.equal(left, right)
    elif isinstance(left, dict):
        assert left.keys() == right.keys()
        for key in left:
            _exact(left[key], right[key])
    elif isinstance(left, (tuple, list)):
        assert len(left) == len(right)
        for a, b in zip(left, right):
            _exact(a, b)
    elif isinstance(left, float) and np.isnan(left):
        assert np.isnan(right)
    else:
        assert left == right


def _rng():
    return random.getstate(), np.random.get_state(), torch.get_rng_state()


def _restore(state):
    random.setstate(state[0])
    np.random.set_state(state[1])
    torch.set_rng_state(state[2])


def _bank(*, fps, randomize):
    env, model = _env(seconds=1.24, randomize=randomize), _Model()
    rendered, annotated, annotate = _renderer(env)
    records = []
    try:
        for jitter in (False, True):
            if jitter:
                env.cfg.setdefault("reset", {}).update({
                    "start_jitter_deg": 3.0, "start_bad_prob": 0.25,
                    "start_bad_max_joints": 1, "start_bad_deg_min": 8.0,
                    "start_bad_deg_max": 16.0})
            for deterministic in (True, False):
                for index in range(6):
                    trace, timing = [], {}
                    kwargs = {"video_fps": fps} if fps is not None else {}
                    ep, frames = evaluation.run_episode(
                        env, model, deterministic=deterministic, video=True,
                        annotate=annotate, trace_sink=trace,
                        video_timing=timing, **kwargs)
                    records.append(dict(cell=(jitter, deterministic, index),
                                        ep=ep, trace=trace, frames=frames,
                                        timing=timing))
        return dict(records=records, rng=_rng(),
                    env_rng=copy.deepcopy(env.rng.bit_generator.state),
                    counts=(model.reset_calls, model.noise_calls,
                            model.predict_calls),
                    rendered=rendered, annotated=annotated)
    finally:
        env.close()


@pytest.mark.parametrize("randomize", [False, True], ids=["dr0", "dr02"])
def test_pacing_preserves_sequential_24_episode_bank(randomize):
    original = _rng()
    try:
        random.seed(7)
        np.random.seed(11)
        torch.manual_seed(13)
        initial = _rng()
        legacy = _bank(fps=None, randomize=randomize)
        _restore(initial)
        paced = _bank(fps=25.0, randomize=randomize)
    finally:
        _restore(original)
    assert len(legacy["records"]) == len(paced["records"]) == 24
    # Exercise actual commanded walking after the one-second startup hold.
    assert any(record["ep"].get("cmd_dist_m", 0.0) > 0.0
               for record in legacy["records"])
    assert legacy["counts"][:2] == paced["counts"][:2] == (24, 24)
    for key in ("counts", "rng", "env_rng"):
        _exact(legacy[key], paced[key])
    for old, new in zip(legacy["records"], paced["records"]):
        for key in ("cell", "ep", "trace"):
            _exact(old[key], new[key])
        assert len(old["trace"]) > 0
        assert len(old["frames"]) == len(old["trace"])
        assert old["timing"]["requested_fps"] is None
        assert old["timing"]["fps"] == 25.0
        assert old["timing"]["encoded_seconds"] == pytest.approx(
            len(old["trace"]) / 25.0)
        assert new["timing"]["frame_count"] == len(new["frames"])
        assert new["timing"]["capture_times_s"][-1] == pytest.approx(
            new["trace"][-1]["t_s"])
        for frame, capture_time in zip(
                new["frames"], new["timing"]["capture_times_s"]):
            tick = int(round(capture_time / 0.01))
            np.testing.assert_array_equal(frame, old["frames"][tick - 1])
    assert len(paced["rendered"]) < len(legacy["rendered"])
    for bank in (legacy, paced):
        assert len(bank["rendered"]) == len(bank["annotated"])


@pytest.mark.parametrize("hz,fps,steps,expected", [
    (100, 25, 20, [4, 8, 12, 16, 20]),
    (60, 25, 30, [3, 5, 8, 10, 12, 15, 17, 20, 22, 24, 27, 29, 30]),
    (10, 10, 3, [1, 2, 3]),
    (100, 25, 1, [1]),
    (100, 25, 6, [4, 6]),
])
def test_capture_deadlines_include_terminal_without_rounding_drift(
        hz, fps, steps, expected):
    clock = evaluation._VideoClock(fps, 1.0 / hz)
    actual = [tick for tick in range(1, steps + 1)
              if clock.due(tick / hz, done=tick == steps)]
    assert actual == expected
    assert clock.fps == fps


@pytest.mark.parametrize("fps", [0, -1, float("nan"), float("inf"), 101])
def test_invalid_or_above_control_fps_rejected(fps):
    with pytest.raises(ValueError):
        evaluation._VideoClock(fps, 0.01)


def test_no_video_does_not_render():
    env = _env(seconds=0.08)
    rendered, annotated, annotate = _renderer(env)
    try:
        ep, frames = evaluation.run_episode(
            env, _Model(), deterministic=True, video=False,
            annotate=annotate, video_fps=25.0)
    finally:
        env.close()
    assert ep["mode"] == "walk"
    assert frames == rendered == annotated == []


def test_paced_metadata_and_encoded_duration(tmp_path):
    import json
    import imageio.v2 as imageio

    env = _env(seconds=0.2)
    _, _, annotate = _renderer(env)
    timing = {}
    try:
        _, frames = evaluation.run_episode(
            env, _Model(), deterministic=True, video=True,
            annotate=annotate, video_fps=25.0, video_timing=timing)
    finally:
        env.close()
    assert timing["requested_fps"] == timing["fps"] == 25.0
    assert timing["control_dt_s"] == 0.01
    assert timing["simulated_seconds"] == pytest.approx(0.2)
    assert timing["frame_count"] == len(frames) == 5
    assert timing["encoded_seconds"] == pytest.approx(0.2)
    assert timing["capture_times_s"] == pytest.approx([.04, .08, .12, .16, .2])
    output = tmp_path / "paced"
    evaluation._save_video(frames, output, timing=timing)
    with imageio.get_reader(output.with_suffix(".mp4")) as reader:
        metadata = reader.get_meta_data()
        assert metadata["fps"] == pytest.approx(25.0)
        assert metadata["duration"] == pytest.approx(0.2, abs=0.001)
        assert reader.count_frames() == 5
    _exact(json.loads(output.with_suffix(".video.json").read_text()), timing)


def test_early_termination_is_captured_before_first_deadline():
    env = _env(seconds=0.2)
    rendered, _, annotate = _renderer(env)
    step = env.step

    def terminate_at_second_tick(action):
        obs, reward, term, trunc, info = step(action)
        if env._step_i == 2:
            term = True
            info = {**info, "termination_reason": "test_early_stop"}
        return obs, reward, term, trunc, info

    env.step = terminate_at_second_tick
    timing, trace = {}, []
    try:
        ep, frames = evaluation.run_episode(
            env, _Model(), deterministic=True, video=True,
            annotate=annotate, video_fps=25.0, video_timing=timing,
            trace_sink=trace)
    finally:
        env.close()
    assert ep["terminated"]
    assert ep["term_reason"] == "test_early_stop"
    assert len(trace) == 2
    assert rendered == [2]
    assert len(frames) == timing["frame_count"] == 1
    assert timing["capture_times_s"] == pytest.approx([0.02])
    assert timing["simulated_seconds"] == pytest.approx(0.02)
    assert timing["encoded_seconds"] == pytest.approx(0.04)


def test_legacy_encoder_keeps_25fps_without_timing_sidecar(tmp_path):
    import imageio.v2 as imageio

    frames = [np.full((16, 16, 3), i, dtype=np.uint8) for i in range(6)]
    output = tmp_path / "legacy"
    evaluation._save_video(frames, output)
    with imageio.get_reader(output.with_suffix(".mp4")) as reader:
        metadata = reader.get_meta_data()
        assert metadata["fps"] == pytest.approx(25.0)
        assert metadata["duration"] == pytest.approx(0.24, abs=0.001)
        assert reader.count_frames() == 6
    assert not output.with_suffix(".video.json").exists()
