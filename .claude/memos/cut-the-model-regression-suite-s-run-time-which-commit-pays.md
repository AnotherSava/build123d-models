---
created: 2026-10-19 06:36:47
---

# Cut the model regression suite's run time, which /commit pays on every commit

The model regression suite (venv/Scripts/python.exe -m pytest tests/ -m regression) took 375 s for 14 models on 2026-10-17, and .claude/commit-checks.sh runs it on every /commit, where /commit's step 9 gate (gate_pushed_tree.py) can run it a second time. The newest model, planter_tray (src/sava/csg/build123d/models/hydroponics/plantertray.py), alone takes about 60-70 s to rebuild: it fits a three-line Caveat text label (PlanterTray._fit_label is ~0.5 s; the rest is OCC booleans and text extrusion),. How the other 13 models split the remaining time was not measured. Next step: time each model separately (pytest --durations=0 -m regression), find where each build spends its time, then decide among: parallel runs (pytest-xdist), caching a model's signature keyed by a hash of its source and the common modules it imports, or running only the models whose imports a change touched. A proposal to skip the redundant second gate run when HEAD's tree equals the one already gated went to the dotfiles session (claude-f4) on 2026-10-17; that part is not this repo's to change.
