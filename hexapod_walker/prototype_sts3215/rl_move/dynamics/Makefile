# dynamics (dynrep) — run from anywhere: make -C rl_move/dynamics <target>
HERE  := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
PROTO := $(abspath $(HERE)/../..)
PY    := uv run python

help:                    ## this help
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

collect:                 ## v1 dataset (400 episodes; append-safe, vary --seed via SEED=)
	cd $(PROTO) && $(PY) -m rl_move.dynamics.collect \
	    --out rl_move/dynamics/datasets/v1 --episodes 400 --seed $(or $(SEED),0)

train:                   ## pretrain dyn_v1 on datasets/v1
	cd $(PROTO) && $(PY) -m rl_move.dynamics.train \
	    --data rl_move/dynamics/datasets/v1 --name dyn_v1 --steps 20000

.PHONY: help collect train
