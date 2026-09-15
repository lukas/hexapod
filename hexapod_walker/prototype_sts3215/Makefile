# hexapod prototype: tests, orchestrator state, robot deploy, Mac hub.
# The CAD/print/BuildViz pipeline lives in https://github.com/lukas/hexapod-cad.
#
# Python runs through uv and the shared repo-root venv (created from the
# repo-root pyproject.toml / uv.lock by `uv sync`).

REPO_ROOT := $(abspath $(CURDIR)/../..)
RUN       := $(REPO_ROOT)/run.sh

# ``mujoco.viewer.launch_passive`` requires ``mjpython`` on macOS (it
# needs to own the main thread for Cocoa to spin up an NSApplication).
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
MJ_PY  := uv run mjpython
else
MJ_PY  := uv run python
endif

.PHONY: test test-fast state view view-static robot-video robot-check robot-unit-check robot-resolve robot-status robot-deploy robot-deploy-fast web-8898 web-8898-start web-8898-stop web-8898-restart web-8898-status web-8898-logs vision-check cameras help

# Orchestrator runtime state (ledger directory, run stories, RL_LOG.md) is a
# plain directory at <checkout>/.state (or $HEXAPOD_STATE_DIR), not a git
# repo -- see rl_move/orchestrator/state_dir.py. This copies the LIVE state
# from the controller pod (falls back to the hexapod-state PVC mirror) into
# it. Read-only here; the controller is the only writer.
state:
	bash "$(CURDIR)/rl_move/orchestrator/state_sync.sh" pull

# Tests. The default developer loop skips @pytest.mark.slow rollouts and
# runs in parallel (pytest-xdist is in the dev group). `make test` is the
# whole suite. Rules for adding tests: RESEARCH_RULES.md "Tests".
test-fast:
	uv run pytest -q -n auto -m "not slow" rl_move/tests linux_control robots firmware/tests sysid/tests

test:
	uv run pytest -q -n auto rl_move/tests linux_control robots firmware/tests sysid/tests

help:
	@echo "Hexapod prototype targets:"
	@echo "  test-fast         Parallel suite without @slow rollouts (the developer loop)."
	@echo "  test              Whole suite."
	@echo "  state             Pull the orchestrator's live state dir (ledger, journals) into .state."
	@echo "  view              Open the interactive MuJoCo viewer with the primitive model walking in tripod gait."
	@echo "  view-static       Same viewer, legs frozen in the standing-pose keyframe (--no-gait)."
	@echo "  robot-check       Fast linux_control syntax/JS/diff checks; no robot access."
	@echo "  robot-unit-check  robot-check plus fake-bus/off-robot control tests."
	@echo "  robot-resolve     Refresh/print cached robot IP for hexapod.local."
	@echo "  robot-status      Read-only robot web health summary."
	@echo "  robot-deploy      robot-check + SSH deploy + remote compile + health."
	@echo "  robot-deploy-fast robot-check + SSH deploy only; deploy waits for /api/ping."
	@echo "  web-8898-start    Start the Mac hub at https://localhost:8443/rl + HTTP :8898."
	@echo "  web-8898-status   Check the local HTTP/HTTPS hub and robot proxy target."
	@echo "  vision-check      Run the hexapod-tracker checks and the off-robot gait-survey tests."
	@echo "  cameras           Open the camera server page at http://localhost:8766/."
	@echo "  robot-video       Contact sheet from a diagnosis MOV/MP4: make robot-video VIDEO=/path/movie.mov."
	@echo "  CAD, BOM, printing, BuildViz: https://github.com/lukas/hexapod-cad"

# Open the interactive MuJoCo viewer (passive mode) with the primitive
# model in the procedurally generated terrain + obstacle world.  Forward
# `make view ARGS=...` any extra CLI flag from mujoco_prototype.py, e.g.:
#   make view ARGS="--vx 0.20 --no-terrain --obstacles 0"
view:
	cd $(REPO_ROOT) && $(MJ_PY) hexapod_walker/prototype_sts3215/mujoco_prototype.py $(ARGS)

view-static:
	cd $(REPO_ROOT) && $(MJ_PY) hexapod_walker/prototype_sts3215/mujoco_prototype.py --no-gait --no-terrain --obstacles 0 $(ARGS)

robot-video:
	@if [ -z "$(VIDEO)" ]; then echo "usage: make robot-video VIDEO=/path/movie.mov [TIMES=0,8,16] [CROP=.0,.33,1,.98]" >&2; exit 2; fi
	$(RUN) hexapod_walker/prototype_sts3215/linux_control/video_contact_sheet.py \
		"$(VIDEO)" $(if $(TIMES),--times "$(TIMES)",) $(if $(CROP),--crop "$(CROP)",)

robot-check:
	bash "$(CURDIR)/linux_control/dev_loop.sh" check

robot-unit-check:
	bash "$(CURDIR)/linux_control/dev_loop.sh" unit-check

robot-resolve:
	bash "$(CURDIR)/linux_control/dev_loop.sh" resolve

robot-status:
	bash "$(CURDIR)/linux_control/dev_loop.sh" status

robot-deploy:
	bash "$(CURDIR)/linux_control/dev_loop.sh" deploy

robot-deploy-fast:
	bash "$(CURDIR)/linux_control/dev_loop.sh" deploy-fast

web-8898 web-8898-start:
	bash "$(CURDIR)/sim_viewer/hexapod_web_8898.sh" start

web-8898-stop:
	bash "$(CURDIR)/sim_viewer/hexapod_web_8898.sh" stop

web-8898-restart:
	bash "$(CURDIR)/sim_viewer/hexapod_web_8898.sh" restart

web-8898-status:
	bash "$(CURDIR)/sim_viewer/hexapod_web_8898.sh" status

web-8898-logs:
	bash "$(CURDIR)/sim_viewer/hexapod_web_8898.sh" logs

vision-check:
	$(MAKE) -C "$(CURDIR)/hexapod-tracker" check
	cd "$(CURDIR)" && uv run pytest -q linux_control/test_gait_survey.py

cameras:
	@command -v open >/dev/null 2>&1 && open "http://127.0.0.1:8766/" || echo "http://127.0.0.1:8766/"
