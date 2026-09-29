"""Apply a conservative PLA / textured PEI H2D calibration-board process.
Run with uv run python tune_print.py after make_board.py.
"""
from pathlib import Path
import json
import zipfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'aprilgrid_400-419_H2D_tower_clearance.3mf'
OUTPUT = HERE / 'aprilgrid_400-419_H2D_quality_PLA.3mf'

with zipfile.ZipFile(SOURCE) as archive:
    entries = {name: archive.read(name) for name in archive.namelist()}
settings = json.loads(entries['Metadata/project_settings.config'])
updates = {
    'print_settings_id': 'AprilGrid H2D - quality PLA 0.20mm',
    'curr_bed_type': 'Textured PEI Plate',
    'layer_height': '0.2',
    'initial_layer_print_height': '0.2',
    'wall_loops': '3',
    'bottom_shell_layers': '5',
    'bottom_shell_thickness': '1',
    'top_shell_layers': '5',
    'top_shell_thickness': '1',
    'sparse_infill_density': '25%',
    'sparse_infill_pattern': 'gyroid',
    'top_surface_pattern': 'monotonicline',
    'ironing_type': 'no ironing',
    'initial_layer_speed': '25',
    'initial_layer_infill_speed': '40',
    'outer_wall_speed': '60',
    'inner_wall_speed': '120',
    'top_surface_speed': '40',
    'internal_solid_infill_speed': '120',
    'sparse_infill_speed': '150',
    'gap_infill_speed': '60',
    'default_acceleration': '4000',
    'outer_wall_acceleration': '1500',
    'top_surface_acceleration': '1000',
    'additional_cooling_fan_speed': '0',
    'textured_plate_temp': '60',
    'textured_plate_temp_initial_layer': '60',
    'enable_support': '0',
    'brim_type': 'no_brim',
    'skirt_loops': '0',
    'enable_prime_tower': '1',
    'flush_into_infill': '0',
}
# Preserve the installed Bambu Studio profile's vector lengths and value types.
for key, value in updates.items():
    assert key in settings, key
    old = settings[key]
    settings[key] = [value] * len(old) if isinstance(old, list) else value
entries['Metadata/project_settings.config'] = json.dumps(settings, indent=2).encode()
with zipfile.ZipFile(OUTPUT, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name, data in entries.items():
        archive.writestr(name, data)
(HERE / 'quality_print_settings.json').write_text(json.dumps(updates, indent=2) + '\n')
print(OUTPUT)
