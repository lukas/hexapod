"""Mechanics-only test for the rl_only FULL-lifecycle (rise->walk->
turn->lower) composition tool's pure aggregation helper -- no mujoco/
PPO/rollouts, per RESEARCH_RULES "Tests"."""
from rl_move.sim.eval_lifecycle_full_rlonly import summarize_segments


def test_summarize_segments_counts_per_segment_success_and_zero_fall():
    episodes = [
        {"zero_fall": True, "segments": [
            {"seg": "rise", "success": True},
            {"seg": "walk", "success": True},
            {"seg": "turn", "success": True},
            {"seg": "lower", "success": True},
        ]},
        {"zero_fall": False, "segments": [
            {"seg": "rise", "success": True},
            {"seg": "walk", "success": False},
        ]},
    ]
    out = summarize_segments(episodes)
    assert out["episodes"] == 2
    assert out["zero_fall_episodes"] == "1/2"
    assert out["rise_reached"] == 2 and out["rise_success"] == 2
    assert out["walk_reached"] == 2 and out["walk_success"] == 1
    # turn/lower only reached by the first (surviving) episode
    assert out["turn_reached"] == 1 and out["turn_success"] == 1
    assert out["lower_reached"] == 1 and out["lower_success"] == 1


def test_summarize_segments_empty_episodes_is_zero_over_zero():
    out = summarize_segments([])
    assert out["zero_fall_episodes"] == "0/0"
    assert "rise_reached" not in out


def test_summarize_segments_missing_segment_type_omitted():
    episodes = [{"zero_fall": True, "segments": [
        {"seg": "rise", "success": True},
        {"seg": "walk", "success": True},
    ]}]
    out = summarize_segments(episodes)
    assert "turn_reached" not in out
    assert "lower_reached" not in out
