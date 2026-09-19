"""replay_compare motion-onset alignment (the real robot starts stepping some seconds
after drive-start, on a clock that differs from the camera, so we anchor on real motion)."""
from rl_move.sim.replay_compare import find_motion_onset


def test_onset_is_first_sustained_motion_not_the_start():
    # frozen (stand/settle) for 1 s, then motion begins at 1.0 s
    motion = [(i * 0.1, 0.02) for i in range(10)] + [(1.0, 0.4), (1.1, 0.9)]
    assert find_motion_onset(motion, thresh=0.25) == 1.0


def test_onset_falls_back_to_first_sample_if_never_moves():
    motion = [(0.0, 0.01), (0.1, 0.02)]
    assert find_motion_onset(motion, thresh=0.25) == 0.0


def test_onset_empty():
    assert find_motion_onset([], thresh=0.25) == 0.0
