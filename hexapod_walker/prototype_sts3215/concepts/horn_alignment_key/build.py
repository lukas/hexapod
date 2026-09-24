"""Two-pin temporary horn alignment key. Dimensions in mm.

uv run --with build123d --with trimesh python build.py
"""
from pathlib import Path
import json
from build123d import Box, Cylinder, Cone, Pos, Align, export_step, export_stl
import trimesh

HERE = Path(__file__).resolve().parent
OUT = HERE / 'stl'
OUT.mkdir(exist_ok=True)
A = (Align.CENTER, Align.CENTER, Align.MIN)
PITCH = 14.0
# Source: cnc_chorn_overhead (3 mm blade + 4/4.5 mm boss),
# premade_chorn_56/hardware_config.toml (2.1 mm plate + 7 mm spacer).
STACKS = {'premade_spacer_9p1': 9.1, 'cnc_drive_7p0': 7.0,
          'cnc_passive_7p5': 7.5, 'bare_plate_2p1': 2.1}

def box(x,y,z,dx,dy,dz):
    return Pos(x,y,z)*Box(dx,dy,dz,align=A)

def cyl(x,y,z,d,h):
    return Pos(x,y,z)*Cylinder(d/2,h,align=A)

def key(stack):
    # Transverse bridge at y=0 leaves both unoccupied holes at y=±7 open.
    p=box(0,0,0,21,5.5,4)
    # Side handle stays outside the screw/driver paths; press axially by hand.
    p+=box(-21,0,0,25,9,4)
    p-=cyl(-28,0,-1,3.5,6)
    for x,reach in [(-7,1.5),(7,1.0)]:
        p+=cyl(x,0,4,3.1,stack-0.3)
        p+=Pos(x,0,4+stack-0.3)*Cone(1.55,1.1,0.3,align=A)
        p+=cyl(x,0,4+stack,2.2,reach-0.6)
        p+=Pos(x,0,4+stack+reach-0.6)*Cone(1.1,0.4,0.6,align=A)
    # Central relief bridges over a protruding centre screw head.
    p-=box(0,0,1,6.5,6,3.1)
    return p

parts={f'key_{label}':key(s) for label,s in STACKS.items()}
stack=9.1
# Schematic stack: holes conservatively represented as 3.4 mm clearance.
bracket=cyl(0,0,4,22,stack)
horn=cyl(0,0,4+stack,20,3)
for x,y in [(7,0),(-7,0),(0,7),(0,-7)]:
    bracket-=cyl(x,y,3,3.4,stack+2)
    # 2.4 is an assumed clear envelope, NOT a measured thread minor diameter.
    horn-=cyl(x,y,3+stack,2.4,5)
bracket-=cyl(0,0,3,8,stack+2)
horn-=cyl(0,0,3+stack,3.4,5)
parts['reference_bracket_spacer_DO_NOT_PRINT']=bracket
parts['reference_horn_DO_NOT_PRINT']=horn
checks={}
for name,p in parts.items():
    assert p.is_valid and len(p.solids())==1, name
    export_stl(p,OUT/f'{name}.stl',tolerance=0.025,angular_tolerance=0.1)
    if name.startswith('key_'): export_step(p,HERE/f'{name}.step')
    mesh=trimesh.load(OUT/f'{name}.stl',force='mesh')
    assert mesh.is_watertight and mesh.is_volume,name
    checks[name]={'watertight':True,'volume_mm3':float(mesh.volume),'bounds_mm':mesh.bounds.tolist()}
k=parts['key_premade_spacer_9p1']
for ref in (bracket,horn): assert (k & ref).volume<1e-6
for y in (-7,7):
    # Tool clearance for 6 mm diameter driver at the two free holes.
    assert (k & cyl(0,y,-1,6,25)).volume<1e-6
for withdrawal in (0,0.5,1,2,5,10,12):
    moved=Pos(0,0,-withdrawal)*k
    assert (moved & bracket).volume<1e-6
    assert (moved & horn).volume<1e-6
checks['assembly']={'nominal_stack_mm':9.1,'thread_clear_envelope_assumption_mm':2.4,
    'driver_clearance_diameter_mm':6,'withdrawal_sample_count':7,
    'physical_fit_tested':False,'holding':'Hand-held axial pressure; not a latch or clamp'}
(HERE/'checks.json').write_text(json.dumps(checks,indent=2)+'\n')
scene={'name':'Horn alignment key — two temporary pins — v1','units':'mm','center':[0,0,8],
       'meshes':[{'id':n,'name':n,'url':f'stl/{n}.stl'} for n in ['key_premade_spacer_9p1','reference_bracket_spacer_DO_NOT_PRINT','reference_horn_DO_NOT_PRINT']], 'instances':[]}
def inst(mesh,label,x,z=0,color='#34b7cf',reference=False):
    scene['instances'].append({'id':label,'name':label,'meshId':mesh,'partType':mesh,'color':color,
      'role':'reference' if reference else 'printed','cots':reference,
      'transform':[1,0,0,0,0,1,0,0,0,0,1,0,x,0,z,1]})
inst('key_premade_spacer_9p1','1 — Tool alone: long pin enters first',-55)
inst('key_premade_spacer_9p1','2 — Exploded: tool / clamp stack / horn',0)
inst('reference_bracket_spacer_DO_NOT_PRINT','Exploded bracket and spacer',0,12,'#9ba7b3',True)
inst('reference_horn_DO_NOT_PRINT','Exploded horn (holes schematic)',0,19,'#e9b45e',True)
inst('key_premade_spacer_9p1','3 — Hold key against face; start other two screws',55)
inst('reference_bracket_spacer_DO_NOT_PRINT','Aligned bracket and spacer',55,0,'#9ba7b3',True)
inst('reference_horn_DO_NOT_PRINT','Aligned horn',55,0,'#e9b45e',True)
(HERE/'scene.json').write_text(json.dumps(scene,indent=2)+'\n')
print(json.dumps(checks,indent=2))
