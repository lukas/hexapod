# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s7-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RETENTION_PASS_NARROW

**created**: 2026-09-08T10:09:08+00:00

**pod**: hexapod-mjx-train-1

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s7-acq1

**wandb_id**: wlq0i0k6

**hypothesis**: Matched joint-space (OFF) control for the halfgrav cont10m durability read above: does this arm's own 40M performance (0 falls, slip 1.90/1.91/1.83/1.93, det-mode leg-underuse quirk already precedented non-blocking) hold steady at 10M more steps, so the paired ON/OFF slip ratio at 50M is a valid comparison and not confounded by drift in the control itself? Byte-identical continuation recipe to the ON sibling except no cart_foot keys (joint-space action decode).

**gate**: MATCHED CONTROL: read together with cartfoot-halfgrav-s7-acq1-cont10m at the same budget. Retention = 0 new falls and slip/m within noise (+/-20%) of this arm's own 40M read (1.90/1.91/1.83/1.93); any regression here means the ON/OFF ratio comparison at 50M needs re-basing on the control's own drift, not read as an ON-side effect.

**verdict**: OFF (joint-space) +10M continuation to 50M cumulative clears its own narrow retention gate (0 new falls, slip/m within +/-20% of the 40M read: this read 1.76/1.97/1.78/1.98 vs 40M's 1.90/1.91/1.83/1.93 -- all in-band, 0 terms in all 24 episodes) but its six-leg gait validity got WORSE, not just held: gait_valid 0/6,4/6,0/6,3/6=7/24 vs the 40M read's 0/6,5/6,0/6,5/6=10/24 -- both stochastic groups lost an extra passing episode (leg1 now sacrificed in 2/6 walk/sto and 3/6 walk_startjitter/sto, up from 1/6 each), while the deterministic groups' chronic leg1/4 double-sacrifice (0/6 both groups) persists unchanged at both reads. Reward still rising (quarters 280/820/1389/1704, ep_rew_mean 1728) so this is not a flat-reward FAIL by the 08-21 ruling, and the pre-registered gate text only conditions retention on falls+slip -- both hold -- so this is a technical PASS on its own terms, not a hardening. Net effect: the ON/OFF gait-quality gap WIDENS at 50M (22/24 vs 7/24) versus 40M (22/24 vs 10/24), reinforcing rather than narrowing the cart_foot-vs-joint-space result at this seed/depth. Read together with the ON cont10m sibling verdicted this same cycle.

