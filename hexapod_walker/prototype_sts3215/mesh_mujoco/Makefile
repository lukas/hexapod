.PHONY: build view view-stance clean

build:
	uv run --with numpy --with scipy --with shapely --with trimesh python build_mesh_model.py

view:
	./view_mesh.sh plant

view-stance:
	./view_mesh.sh stance

clean:
	rm -rf assets hexapod_mesh.xml
