UV_CAD = uv run --no-project --python 3.12 --with build123d --with trimesh --with numpy
BUILDVIZ = npx buildviz
BUILD_DIR = out

.PHONY: build check view-buildviz push-cloud pack

build:
	$(UV_CAD) python build_tt_truck.py

check: build
	$(UV_CAD) python build_tt_truck.py --check-only
	cd /Users/lukas/buildviz && npm run buildviz -- compat /Users/lukas/hexapod/hexapod_walker/tt_kid_truck/out --json
	cd /Users/lukas/buildviz && npm run buildviz -- validate /Users/lukas/hexapod/hexapod_walker/tt_kid_truck/out --json
	cd /Users/lukas/buildviz && npm run buildviz -- check /Users/lukas/hexapod/hexapod_walker/tt_kid_truck/out --emit --json

view-buildviz: check
	cd /Users/lukas/buildviz && npm run buildviz -- push --project tt-kid-truck --build chassis --version main --no-snapshot --scene /Users/lukas/hexapod/hexapod_walker/tt_kid_truck/out/scene.json --upload-assets -m "add removable classic pickup cab, hood, open bed, wheel arches, grille, and lights"
	-$(MAKE) push-cloud

push-cloud:
	-cd ../prototype_sts3215 && uv run python tools/push_cloud_buildviz.py --build-id tt-kid-truck/chassis

pack: check
	cd /Users/lukas/buildviz && npm run buildviz -- pack /Users/lukas/hexapod/hexapod_walker/tt_kid_truck/out --assembly printable --printer x1c --export --out /Users/lukas/hexapod/hexapod_walker/tt_kid_truck/out/plates
