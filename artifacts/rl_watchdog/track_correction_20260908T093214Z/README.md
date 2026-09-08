# Scratch track metadata correction

Six exact seed40 source/torque-retain/narrow-heading records were mislabeled
joystick. The recorded script used launch_run.cmd_update (ledger lock and
atomic writes) and the authenticated W&B API to classify them as walkcurr.
Receipt verifies all six labels/tags and unchanged historical command hashes.
No process, checkpoint, gate, simulation cfg, or original hypothesis changed.

Published/deployed d1523245b also adds the missing cw-walkscratch prefix
mapping for future untagged launches. Four direct mapping checks passed;
existing explicit source/track inheritance is unchanged. The six source
metadata fixes ensure their future respec descendants inherit walkcurr.
The command's original WANDB_TAGS remains historical launch provenance.
