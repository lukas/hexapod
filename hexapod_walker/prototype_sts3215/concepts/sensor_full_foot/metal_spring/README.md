# PETG foot with metal return springs — bench prototype

Two PETG prints replace the TPU collar design. The rounded foot is now 28 mm OD to accommodate three external spring/retainer stations at 11 mm radius. The socket remains 16 mm OD, 8.2 mm bore for nominal 8 mm rod, 20 mm tall. Sensor reference remains 10 mm OD with assumed 8.5 mm active area and 0.2 mm film/adhesive stack.

## Hardware per foot

- Three metal spacer sleeves: 3 mm OD, 2.2 mm ID, exactly 7 mm long, square/deburred ends.
- Three M2 x 12 mm screws, length measured under head. Printed foot has 1.7 mm pilot holes; tap M2 carefully and verify thread retention.
- Three M2 washers: model uses 5 mm OD, 2.2 mm ID, 0.5 mm thick.
- Three light compression springs: illustrative assembled envelope 4.6 mm OD, 4 mm ID, 5 mm installed length, 0.3 mm wire. These are reference geometry, NOT an identified purchasable spring or verified spring specification. Select actual springs with slight preload at 5 mm installed length and solid height below 4.4 mm; measure total activation force. Spring free length/rate/material/end style remain to be selected. Rendered helices do not model closed/ground ends or deformation.
- One 6.5 mm diameter x 1 mm silicone sheet pad, cut by hand, plus sensor and adhesive. Silicone hardness remains to be tested.

## Assembly and operation

Attach sensor to foot and silicone pad under socket web. Put sleeves and springs at the three foot stations. Slide socket ear holes over sleeves. Install washers and screws: tighten against sleeves, not the moving socket ears. Washers retain ears at rest; ears slide down the sleeves 0.6 mm. The outer socket rim then contacts foot as a rigid travel stop. Do not glue the sliding joint. Wire exits on the side without a spring station.

The assumed 0.2 mm pad-to-sensor gap leaves nominal 0.4 mm silicone compression at the stop. Measure actual stack and adjust pad thickness: stop limits displacement, not known sensor force. Check return, retention, angled contact, thread strength and sensor threshold before robot use. No spring force, fatigue, friction or load capacity is validated.

## Printing

petg_all_parts.3mf contains both PETG parts, oriented and separated. Foot sensor face down; socket open rod end down. Inspect support needs under the socket ears and bridging over the rod socket in slicer preview. Do not print the hardware, sensor or silicone references. No TPU is needed.

Geometry checks: all reference and printed meshes watertight; seven rigid travel positions clear foot/sensor/sleeves/washers/screws; positive stop at overtravel; full pad backing. Actual springs and silicone deformation are not simulated. Metal sleeves replace printed guide pins. 3.5 mm guide holes provide nominal 0.5 mm diametral clearance on 3 mm sleeves; finish holes as needed for free motion.
