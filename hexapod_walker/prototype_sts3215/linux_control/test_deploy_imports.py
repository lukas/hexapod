"""Import the real staged bundle with historical duplicate modules present."""
import os
from pathlib import Path
import subprocess

import pytest


HERE = Path(__file__).resolve().parent
CHECKOUT = HERE.parents[2]


@pytest.fixture
def staged_bundle(tmp_path):
    stage = tmp_path / 'bundle'
    subprocess.run(
        ['bash', '-c', 'source "$1"; stage_deploy_tree "$2" "$3"',
         'stage-test', str(HERE / 'deploy_manifest.sh'), str(stage), str(HERE)],
        check=True, capture_output=True, text=True, timeout=3)
    # These old flat-layout files remain on upgraded boards; importing them
    # is a failure even when the canonical directories already occur later
    # in PYTHONPATH. A clean checkout alone cannot reproduce that ordering.
    for name in ('feetech_bus', 'motion_telemetry'):
        (stage / 'linux_control' / f'{name}.py').write_text(
            f'raise RuntimeError("stale flat-layout {name} imported")\n')
    return stage


@pytest.mark.parametrize('entrypoint', ['drive_controller', 'web_drive'])
def test_staged_entrypoint_prefers_canonical_modules(staged_bundle, entrypoint, monkeypatch):
    monkeypatch.setenv('HEXAPOD_MODEL_SOURCE', 'sts3215')
    stage = staged_bundle
    lc = stage / 'linux_control'
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(map(str, (
        lc, lc / 'vendor', stage / 'motor_setup', stage))),
        PYTHONDONTWRITEBYTECODE='1')
    script = '''
import importlib
import importlib.util
from pathlib import Path
import sys
stage = Path(sys.argv[2])
class BeforeBenchApi:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'bench_api':
            for name in ('feetech_bus', 'motion_telemetry'):
                origin = Path(importlib.util.find_spec(name).origin)
                assert origin == stage / 'motor_setup' / (name + '.py')
        return None
sys.meta_path.insert(0, BeforeBenchApi())
importlib.import_module(sys.argv[1])
import feetech_bus, motion_telemetry, motor_dynamics
assert Path(feetech_bus.__file__) == stage / 'motor_setup' / 'feetech_bus.py'
assert Path(motion_telemetry.__file__) == stage / 'motor_setup' / 'motion_telemetry.py'
assert Path(motor_dynamics.__file__) == stage / 'linux_control' / 'motor_dynamics.py'
assert feetech_bus.robot_pose_to_raw_degrees([0., 10., 30.] * 6)[2] == 20.
assert motor_dynamics.raw_degree_to_count is feetech_bus.raw_degree_to_count
'''
    result = subprocess.run(
        ['uv', 'run', '--project', str(CHECKOUT), 'python', '-c', script,
         entrypoint, str(stage)], cwd=lc, env=env, capture_output=True,
        text=True, timeout=3)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (lc / 'motor_dynamics.py').read_bytes() == (HERE / 'motor_dynamics.py').read_bytes()
