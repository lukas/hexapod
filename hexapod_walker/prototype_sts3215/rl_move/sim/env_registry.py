"""Task name -> CPU env class, shared by the trainers and the sim tools."""
from __future__ import annotations

from .sim_env import SimHexapodBalanceEnv
from .goal_task import SimHexapodGoalEnv
from .joint_task import SimHexapodJointGoalEnv
from .walk_task import SimHexapodJointWalkEnv

ENV_CLASSES = {"balance": SimHexapodBalanceEnv, "goal": SimHexapodGoalEnv,
               "joint_goal": SimHexapodJointGoalEnv,
               "joint_walk": SimHexapodJointWalkEnv}
