"""Regression suite guarding committed models against silent geometry changes
when common functionality evolves.

Add a model by giving its module a `build() -> ModelSpec` and registering it in
`MODEL_BUILDERS` below, then create its baseline once:

    MODEL_REGRESSION_REBASELINE=1 venv/Scripts/python.exe -m pytest \
        tests/sava/csg/build123d/models/test_model_regression.py

Commit the resulting `signature.json` alongside the model. Thereafter the suite
rebuilds each model, exercises the real 3MF+STL export pipeline into a temp dir,
and asserts the geometry signature still matches the committed baseline. When a
change to a model's geometry is intentional, re-run with the same env var to
bless it. See `_signature.py` for why we compare invariants, not mesh bytes.
"""

import os

import pytest

from sava.csg.build123d.common.modelspec import export_model
from sava.csg.build123d.models.hydroponics import basket, splitter, stand, tray
from sava.csg.build123d.models.other import cableholder, dispenserbottlemount, markerholder, pipeclamp, poweradapters

from ._signature import compare, load_reference, save_reference, signature

# The suite is slow and grows with every model, so it is excluded from the
# default `pytest tests/` run (see pytest.ini) and executed deliberately via
# `-m regression` and the /commit checks (.claude/commit-checks.sh).
pytestmark = pytest.mark.regression

# Registry of covered models — extend one at a time.
MODEL_BUILDERS = {
    "marker_holder": markerholder.build,
    "basket": basket.build,
    "stand": stand.build,
    "pipe_clamp": pipeclamp.build,
    "splitter": splitter.build,
    "dispenser_bottle_mount": dispenserbottlemount.build,
    "tray": tray.build,
    "power_adapters": poweradapters.build,
    "cable_holder": cableholder.build,
}

_REBASELINE = os.environ.get("MODEL_REGRESSION_REBASELINE") == "1"


@pytest.mark.parametrize("model_name", sorted(MODEL_BUILDERS))
def test_model_regression(model_name: str, tmp_path: object) -> None:
    spec = MODEL_BUILDERS[model_name]()
    current = signature(spec)

    if _REBASELINE:
        save_reference(spec, current)
        pytest.skip(f"re-baselined {model_name}")

    # Exercise the real export pipeline (catches mesher / lib3MF regressions),
    # redirected to a temp dir so committed files are untouched.
    export_model(spec, output_root=str(tmp_path))
    assert (tmp_path / spec.name / "export.3mf").exists()

    diffs = compare(current, load_reference(spec))
    assert not diffs, f"geometry drift in '{model_name}':\n" + "\n".join(diffs)


def test_compare_detects_drift() -> None:
    """Self-check: the comparator must flag every kind of change it guards."""
    spec = MODEL_BUILDERS["marker_holder"]()
    base = signature(spec)
    label = next(iter(base))

    assert compare(base, base) == []

    volume_drift = {label: {**base[label], "volume": base[label]["volume"] * 1.01}}
    assert compare(base, volume_drift)

    face_drift = {label: {**base[label], "faces": base[label]["faces"] + 1}}
    assert compare(base, face_drift)

    assert compare(base, {"other_label": base[label]})
