# standwalk STATUS journal archive — 2026-09-03f (VERBATIM trim)

Moved out of STATUS.md 2026-09-03 ~09:4x to keep the live file under
its line budget. This is the 2026-09-03 ~05:0x update entry, verbatim.

Update, 2026-09-03 ~05:0x (idle-kick): item 0's flat-only donegate
session still mid-flight on train-6/7 (~91/90 mp4s, ETA unchanged
~08:3x UTC) -- while it runs, dispatched an EARLY INFORMAL READ on
spare pods (train-2/3, dualbc3-dagger 08-30 fast-read precedent):
walk-mode-only, no video, n=16 det+sto x DR-0+own-DR, SAME train cfg.
**direction_err clearly improved** vs the cap29-acq1 baseline
(46.8deg) on all 8 subgroups/2 seeds: 24.8-35.6deg. **sto/det
convergence holds at acquisition scale**: sto progress_ratio 84-92%
of det (was the old 5-8% collapse) -- canary finding replicates both
seeds. **slip/m MIXED**: dr0-det ties/beats 3.09 (2.83/3.12) but
dr0-sto/owndr-det/owndr-sto read worse (3.39-4.63). Zero falls in all
128 episodes. Reads gate-PARTIAL-shaped (steering fixed, slip not
uniform) not full PASS -- informal proxy only, real verdict still
awaits the video-bearing session. Evidence:
`logs/ckpt_eval/standwalk_stdwalklohi_acq1_{s0,s1}_fastwalkcheck/`.
Also: prior cycle's full-suite regression finished, 39F/256P (was
40F) -- all 5 banks pricing standwalk's LIVE levers (hold/getup/
rise_rock/stopcurrent/trans_drag) now green; remaining reds are 24
RETIRED walkcurr_pf/sv + 1 stale-log getup + 14 non-live-lever banks,
not blocking any funded arm, not chased.
