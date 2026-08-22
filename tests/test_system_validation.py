"""Gate V3 (system validation, full-state AX-21 basis) recorded as an EXPECTED FAILURE.

This file does not certify the system layer; it records, as a documented and
reproducible xfail, that the H2STAR system budget does not reproduce the HSECoE
AX-21 full-state anchor within the pre-registered tolerance.

The gate compares two full-state system metrics against the anchor in
``data/validation/hsecoe_reference.yaml`` (Tamburello et al., SRNL, HSECoE
project ID ST044, 2013):

* ``GC_full = m_h2_full / m_sys`` (kg H2 per kg system), and
* ``VC_full = m_h2_full / V_sys`` (kg H2 per litre of system),

both evaluated at the anchor's full state, 80 K and 200 bar. The numerator is
the FULL-STATE inventory, not the usable swing -- this gate is on a full-state
basis, so ``budget["GC"]`` and ``budget["VC"]`` (which are swing-based, see
:mod:`h2star.system`) are deliberately NOT used.

The +/-15% tolerance is PRE-REGISTERED in ``docs/validation_plan.md`` and is
carried into this file from the anchor YAML at runtime. It must not be edited,
widened, or bypassed to force a pass; doing so would retroactively rewrite the
gate criterion. Likewise the anchor values and the operating state are read from
the YAML rather than hardcoded, so the pre-registered record stays the single
source of truth.

The xfail is ``strict=True`` on purpose: if a future vessel- or BOP-mass upgrade
closes the gap, the test XPASSes and fails the suite, forcing re-adjudication of
Gate V3 rather than letting it pass silently.
"""

from pathlib import Path

import pytest
import yaml

from h2star import isotherm, system

#: Repository root, so the data files resolve regardless of the invocation cwd.
_REPO_ROOT = Path(__file__).resolve().parents[1]

_MATERIAL_YAML = _REPO_ROOT / "data" / "materials" / "ax21.yaml"
_ENGINEERING_YAML = _REPO_ROOT / "data" / "engineering.yaml"
_ANCHOR_YAML = _REPO_ROOT / "data" / "validation" / "hsecoe_reference.yaml"

#: Day-14 sizing-only baseline empty state (Pa, K). This state SIZES the tank to
#: the 5.6 kg usable target; the gate itself reads full-state inventory only.
_P_EMPTY = 5.0e5  # Pa
_T_EMPTY = 160.0  # K

#: bar -> Pa. The anchor pins the full state in bar; the model is strictly SI.
_BAR_TO_PA = 1.0e5

#: m^3 -> L, for the volumetric capacity expressed in kg per litre.
_M3_TO_L = 1000.0


def _load_anchor():
    """Return the parsed Gate V3 anchor document."""
    with open(_ANCHOR_YAML) as fh:
        return yaml.safe_load(fh)


def _full_state_metrics():
    """Compute ``(GC_full, VC_full)`` for the AX-21 system at the anchor state.

    Builds the AX-21 material and its modified D-A isotherm, loads the
    engineering parameters, sizes the tank to the default 5.6 kg usable target,
    and returns the two full-state figures of merit in the anchor's units:
    kg H2 per kg system and kg H2 per litre of system.
    """
    anchor = _load_anchor()
    full_state = anchor["operating_full_state"]

    material = isotherm.Material.from_yaml(_MATERIAL_YAML)
    da = isotherm.ModifiedDA(material)
    engineering = system.EngineeringParams.from_yaml(_ENGINEERING_YAML)

    design = system.SystemDesign(
        material,
        da,
        engineering,
        full_state["pressure_bar"] * _BAR_TO_PA,  # P_full, Pa
        full_state["temperature_K"],  # T_full, K
        _P_EMPTY,  # P_empty, Pa
        _T_EMPTY,  # T_empty, K
    )

    V_internal = system.size_for_usable(design)  # m^3, 5.6 kg usable target
    budget = design.evaluate(V_internal)

    # FULL-STATE basis: numerator is m_h2_full, not the usable swing. The
    # budget's own GC/VC keys are swing-based and are not the gate metric.
    gc_full = budget["m_h2_full"] / budget["m_sys"]  # kg/kg
    vc_full = budget["m_h2_full"] / (budget["V_sys"] * _M3_TO_L)  # kg/L
    return gc_full, vc_full


@pytest.mark.validation
@pytest.mark.xfail(
    strict=True,
    reason=(
        "Gate V3 documented FAIL: engineering-mass block (idealized thin-wall "
        "composite vessel + fixed 16 kg BOP) under-predicts HSECoE Type-3 "
        "system dead mass; GC_full and VC_full exceed the AX-21 full-state "
        "anchor beyond the pre-registered +/-15% band. Localized to the mass "
        "denominator, not the H2 inventory. See GitHub issue #1."
    ),
)
def test_gate_v3_ax21_full_state_system_capacities():
    """GC_full and VC_full must sit within the pre-registered band of the anchor.

    Both metrics are checked in one test so the gate is adjudicated as a single
    pass/fail, matching how Gate V3 is pre-registered.
    """
    anchor = _load_anchor()
    results = anchor["reference_results"]
    gc_anchor = results["system_gravimetric_capacity_kg_per_kg"]["value"]
    vc_anchor = results["system_volumetric_capacity_kg_per_L"]["value"]
    tolerance_pct = anchor["tolerance_pct"]

    gc_full, vc_full = _full_state_metrics()

    gc_band = gc_anchor * tolerance_pct / 100.0
    assert abs(gc_full - gc_anchor) <= gc_band, (
        f"GC_full = {gc_full:.6g} kg/kg is outside the pre-registered "
        f"+/-{tolerance_pct}% band around the anchor {gc_anchor:.6g} kg/kg "
        f"(allowed deviation {gc_band:.6g} kg/kg)."
    )

    vc_band = vc_anchor * tolerance_pct / 100.0
    assert abs(vc_full - vc_anchor) <= vc_band, (
        f"VC_full = {vc_full:.6g} kg/L is outside the pre-registered "
        f"+/-{tolerance_pct}% band around the anchor {vc_anchor:.6g} kg/L "
        f"(allowed deviation {vc_band:.6g} kg/L)."
    )
