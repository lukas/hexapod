# Internal carbon-tube spring foot — geometric prototype

Four PETG parts: rounded sliding foot, external guide, plunger, bonded internal spring stop. Purchased parts: 8 mm OD / 6 mm ID carbon tube, unperforated 10 mm pressure sensor, one kit compression spring (0.3 mm wire, 4 mm OD, 10 mm free length), two M2 x 4 mm retaining screws. No TPU, no hole through sensor, no drilling carbon.

The spring bears between the bonded internal stop and PETG plunger. The plunger's smooth flat 5.6 mm face rests on the sensor. Ground contact raises the foot, sensor and plunger together, compressing the spring. The 12 mm OD foot sleeve slides in a 12.4 mm bore in the external guide. Two radial screws engage closed pockets in the moving sleeve to retain it and prevent rotation; they do not clamp it. A separate annular shoulder stops upward travel at 0.6 mm. Side loads pass through the sleeve/guide rather than intentionally through the film.

## Dimensions and assumptions

- Rounded sole: 19 mm OD, nominal 9.5 mm hemisphere radius.
- Guide: 16 mm OD excluding two screw bosses; 23 mm long.
- Plunger: 5.6 mm OD inside 6 mm rod bore (0.4 mm diametral clearance).
- Internal bonded stop: 5.8 mm OD, 5 mm engagement length, small spring centering pin.
- Spring installed length: 9.5 mm at rest, 8.9 mm at stop. Nominal free length 10 mm gives 0.5 mm preload deflection, 1.1 mm at stop. Rate and actual preload FORCE unknown.
- Sensor reference: 10 mm OD, assumed 8.5 mm active disk, assumed 0.2 mm film plus adhesive. Actual thickness must be measured. Tab width 6.5 mm, wire slot 7.1 mm.
- Rendered spring is an illustrative helix, not a measured coil-count/end-shape model of the purchased kit.

## Assembly

1. Before attaching foot, bond stop into the tube so its bottom spring-bearing face is 13.5 mm above the tube's lower end. Keep adhesive out of spring/plunger bore. Verify bond with bench loading.
2. Bond external guide on rod with guide top 24 mm above rod lower end; keep adhesive out of the lower sliding bore. Carbon tube lower end sits 2 mm above foot sensor seat at nominal rest.
3. Insert spring then plunger through lower tube opening. Plunger centering pin faces spring; its flat underside faces sensor.
4. Attach sensor flat to foot, preserving active area and any vent. Route tab through side slot; allow wire slack for movement.
5. Fit foot sleeve into guide and align pockets with radial holes. Tap 1.7 mm pilots M2. Seat two M2 x 4 mm screws against bosses; tips project into pockets while remaining clear of their floors. No screw enters the carbon tube. Remove screws to service foot.
6. Confirm free sliding and return, no permanent sensor activation, secure retention, and positive stop. Calibrate contact threshold above resting preload; test angled contact repeatedly.

## Printing and limits

`all_petg_parts.3mf` is an unsliced four-object plate. Foot sleeve rim down, guide top down, bonded stop flat top down, plunger flat sensing face down. Inspect bridge over the sensor cavity and supports near screw bosses in slicer preview. Smooth the sensor contact face and sliding surfaces; clear holes/slots as needed. These small printed fits are not physically verified.

All nine meshes are watertight single solids. Seven axial travel positions check foot/sensor/plunger against rod, guide, bonded stop and retaining screws; overtravel intersects compression shoulder; extension overtravel intersects retainer; wire clearances and print transform round trips pass. Screw threads and bond lines are nominal references, not detailed engagement simulations.

The rigid shoulder limits displacement, not a known sensor force. Spring rate, solid height, fatigue, PETG friction/creep, screw-tip slot wear, adhesive strength and oblique-contact binding remain unvalidated. Measure the actual kit spring and sensor stack before committing to all six feet. This is a bench prototype, not a validated robot component.
