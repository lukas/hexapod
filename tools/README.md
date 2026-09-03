# Shared tools

Repository-wide utilities live here. Project-specific generators and checks
stay with their project.

- `push_cloud_buildviz.py` mirrors any local BuildViz build to the configured
  cloud hub. Hexapod and vehicle Makefiles both call this utility.
