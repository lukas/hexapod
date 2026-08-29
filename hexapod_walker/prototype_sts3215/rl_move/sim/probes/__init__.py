"""One-off probe/eval scripts with no live references.

Quarantine (2026-08-29 component-boundaries refactor): scripts land here
only when NOTHING live references them — no rl_docs/RL_LOG entries, no
orchestrator state, no code imports. Anything referenced by path from the
machine-owned docs stays in rl_move/sim/ so recorded commands keep working.
"""
