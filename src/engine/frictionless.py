"""RR-Y1-027 — Ideal / frictionless measurement layer (DEC-064; additive infrastructure).

Every Stage-0 run can now be split into TWO reports off ONE causal pipeline:

  * REALISTIC  -> VERDICT (full money-friction; the existing ``harness`` net path).
  * IDEAL      -> CONCEPT-LEDGER, *never a verdict* (money-friction zeroed, causality
                  physics preserved). The label carries an explicit NON-VERDICT tag.

Strangler / additive: this module consumes ``EngineOutput`` (and a friction spec)
READ-ONLY. It imports no lab code and edits NO committed module -- Mod-A/B/C and
``multiple_testing.py`` are untouched. The verdict-layer numbers it surfaces are the
same ones ``harness`` already computed (additivity is the proof; see the §4 invariant).

------------------------------------------------------------------------------------
§3 -- the load-bearing distinction (if this line blurs, the layer becomes "cheating")
------------------------------------------------------------------------------------
Two force-classes are kept strictly apart:

  MONEY-FRICTION  (zeroed in the ideal layer): commission, slippage, spread,
    execution-timing, AND fill-accessibility / tradability (allocation lottery,
    ceiling-lock, liquidity-depth). The ideal layer assumes a frictionless fill at
    the forward-safe reference price.

  CAUSALITY-PHYSICS (preserved in BOTH layers, never zeroed): look-ahead-safe entry
    (no future leak), survivorship (delisted / bankrupt names are never resurrected),
    the t -> t+1 time arrow. These are laws of physics, not frictions.

Operationally: the position series (signal -> weights -> forward total return) is built
ONCE, upstream, look-ahead-safe (next-open / pre-defined window; ex-post peak selection
is forbidden, DISC-10). The two layers diverge ONLY at the cost-application stage. The
ideal layer gets a frictionless FILL; it never gets a future PEEK.

------------------------------------------------------------------------------------
§4 -- the correctness property (the layer's own measurement-verification anchor)
------------------------------------------------------------------------------------
Because the two layers share the same position series and diverge only at cost
application, the realistic layer with EVERY friction parameter set to its null value
must reproduce the ideal layer BIT-FOR-BIT:

    apply_friction(gross, FrictionParams.null()) == gross == ideal.net_active_ann

``differential_invariant_holds`` asserts exactly this; the golden fixture freezes it.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

import numpy as np

# Explicit, audit-visible labels. The ideal label MUST announce NON-VERDICT so the
# number can never be quoted as a promotion / deploy justification (§5).
LABEL_REALISTIC = "REALISTIC / VERDICT"
LABEL_IDEAL = "IDEAL — NON-VERDICT / CONCEPT-LEDGER"


@dataclass(frozen=True)
class FrictionParams:
    """Money-friction parameters. EVERY field is zeroable; the causal pipeline that
    produced ``gross_active_ann`` is upstream and is NOT represented here (that is the
    whole point of §3 -- causality physics never lives in a friction knob).

    The realistic layer carries the measured friction; the ideal layer carries
    ``FrictionParams.null()`` (all money-friction off, frictionless fill).

    Fields (all annualized fractions unless noted):
      cost_ann          transaction-cost drag (commission + spread + market impact).
      tax_ann           dividend-withholding drag.
      fill_fraction     tradability: fraction of the intended position actually
                        fillable (IPO allocation lottery, secondary ceiling-lock,
                        liquidity depth). 1.0 = frictionless fill; the rest sits in
                        the benchmark/cash leg, so the active return scales by it.
      access_haircut_ann return given up to execution-timing / ceiling-lock slip
                        (you cross later, at a worse reference, than the ideal entry).
    """

    cost_ann: float = 0.0
    tax_ann: float = 0.0
    fill_fraction: float = 1.0
    access_haircut_ann: float = 0.0

    def __post_init__(self) -> None:
        if not (0.0 <= self.fill_fraction <= 1.0):
            raise ValueError(f"fill_fraction must be in [0, 1] (got {self.fill_fraction})")
        if self.cost_ann < 0.0 or self.tax_ann < 0.0:
            raise ValueError("cost_ann / tax_ann must be >= 0 (frictions are non-negative)")

    @classmethod
    def null(cls) -> FrictionParams:
        """The frictionless ideal: no money-cost, no tax, full fill, no access slip."""
        return cls(cost_ann=0.0, tax_ann=0.0, fill_fraction=1.0, access_haircut_ann=0.0)

    @property
    def is_null(self) -> bool:
        return (
            self.cost_ann == 0.0
            and self.tax_ann == 0.0
            and self.fill_fraction == 1.0
            and self.access_haircut_ann == 0.0
        )

    @property
    def tradability_binding(self) -> bool:
        """True when the FILL side (not just money-cost) is what bites -- the
        signature of a friction-grave (a tradability wall, not a cost wall)."""
        return self.fill_fraction < 1.0 or self.access_haircut_ann > 0.0


def apply_friction(gross_active_ann: float, friction: FrictionParams) -> float:
    """Net annualized active return after money-friction (§3). The single cost-
    application rule shared by both layers:

        net = gross * fill_fraction - cost_ann - tax_ann - access_haircut_ann

    ``fill_fraction`` scales the active exposure (partial fill -> partial tilt); the
    additive terms are return drags. With ``FrictionParams.null()`` this is the
    identity ``net == gross`` -- the §4 differential invariant. NaN gross -> NaN
    (the caller degrades; never fabricates a number)."""
    if not np.isfinite(gross_active_ann):
        return float("nan")
    return float(
        gross_active_ann * friction.fill_fraction
        - friction.cost_ann
        - friction.tax_ann
        - friction.access_haircut_ann
    )


def position_fingerprint(active_series) -> str:
    """Stable sha256[:16] of the shared position/active return series, so an auditor
    can confirm the two layers really did consume the SAME causal pipeline (§4). Pure
    function of the values (rounded to 1e-12 to be float-repr stable across platforms)."""
    arr = np.asarray(list(active_series), dtype=float)
    rounded = np.round(arr, 12) + 0.0  # +0.0 normalizes -0.0 -> 0.0
    return hashlib.sha256(rounded.tobytes()).hexdigest()[:16]


@dataclass(frozen=True)
class LayerReport:
    """One layer of the dual report. ``is_verdict`` is the hard switch: the ideal
    layer is is_verdict=False and its ``label`` announces NON-VERDICT (§5)."""

    label: str
    is_verdict: bool
    gross_active_ann: float
    net_active_ann: float
    friction: FrictionParams

    def to_dict(self) -> dict:
        d = {
            "label": self.label,
            "is_verdict": self.is_verdict,
            "gross_active_ann": self.gross_active_ann,
            "net_active_ann": self.net_active_ann,
            "friction": asdict(self.friction),
        }
        if not self.is_verdict:
            # belt-and-braces: the machine-readable form ALSO carries the tag, so a
            # downstream consumer cannot strip the human label and lose the warning.
            d["NON_VERDICT"] = True
            d["concept_ledger"] = True
        return d


@dataclass(frozen=True)
class DualLayerReport:
    """The two reports off one Stage-0 run + a friction-grave classification HINT.

    The hint is exactly that -- a hint. It NEVER auto-classifies: the friction-grave
    vs fact-grave decision is the maintainer's / Orchestrator's call (§5 status-ladder
    hook). ``friction_grave_hint`` therefore always carries ``requires_human=True``."""

    realistic: LayerReport
    ideal: LayerReport
    shared_position_fingerprint: str
    friction_grave_hint: dict

    def to_dict(self) -> dict:
        return {
            "realistic": self.realistic.to_dict(),
            "ideal": self.ideal.to_dict(),
            "shared_position_fingerprint": self.shared_position_fingerprint,
            "friction_grave_hint": self.friction_grave_hint,
            "differential_invariant_holds": self.differential_invariant_holds(),
        }

    def differential_invariant_holds(self) -> bool:
        """§4: the ideal layer must equal the realistic layer re-costed with null
        friction, bit-for-bit. NaN-safe (NaN == NaN treated as holding)."""
        recosted = apply_friction(self.realistic.gross_active_ann, FrictionParams.null())
        a, b = recosted, self.ideal.net_active_ann
        if not np.isfinite(a) and not np.isfinite(b):
            return True
        return a == b


# friction-grave classification thresholds are CALLER-supplied (no hidden magic):
# a candidate needs a STRONG ideal AND a DEAD realistic AND a tradability-bound gap.
def friction_grave_hint(
    realistic: LayerReport,
    ideal: LayerReport,
    *,
    strong_ideal_ann: float,
    dead_realistic_band: float,
) -> dict:
    """Build the (advisory) friction-grave hint. Returns a dict that ALWAYS sets
    ``requires_human=True`` -- the layer makes the classification POSSIBLE, it does
    not MAKE it (§5).

    A friction-grave candidate is: ideal net >= ``strong_ideal_ann`` (the phenomenon
    is real in the frictionless world) AND realistic net <= ``dead_realistic_band``
    (it is dead once costed) AND the kill is driven by the FILL/tradability side, not
    merely money-cost (``friction.tradability_binding``). When the gap is pure money-
    cost the candidate is a plain cost-fail, not a friction-grave."""
    strong = np.isfinite(ideal.net_active_ann) and ideal.net_active_ann >= strong_ideal_ann
    dead = np.isfinite(realistic.net_active_ann) and realistic.net_active_ann <= dead_realistic_band
    tradability_bound = realistic.friction.tradability_binding
    candidate = bool(strong and dead and tradability_bound)
    if candidate:
        reason = (
            "ideal layer shows a strong frictionless phenomenon that the realistic "
            "layer kills via a tradability wall (fill/access), not merely money-cost "
            "-> friction-grave CANDIDATE (save/wait + concept-ledger, distinct from a "
            "fact-grave / graveyard)."
        )
    elif strong and dead:
        reason = (
            "strong ideal, dead realistic, but the kill is pure money-cost (fill is "
            "full, no access slip) -> a plain cost-fail, NOT a friction-grave."
        )
    elif strong:
        reason = "ideal strong but realistic not dead -> not a grave of either kind."
    else:
        reason = "ideal layer not strong -> friction-grave does not apply."
    return {
        "candidate": candidate,
        "reason": reason,
        "strong_ideal": bool(strong),
        "dead_realistic": bool(dead),
        "tradability_bound": bool(tradability_bound),
        "thresholds": {
            "strong_ideal_ann": strong_ideal_ann,
            "dead_realistic_band": dead_realistic_band,
        },
        "requires_human": True,  # classification is the maintainer's / Orchestrator's call
    }


def dual_layer_report(
    gross_active_ann: float,
    realistic_friction: FrictionParams,
    *,
    shared_position_fingerprint: str,
    strong_ideal_ann: float,
    dead_realistic_band: float,
) -> DualLayerReport:
    """Build both layers off ONE gross (one position series). The ideal layer is
    ``gross`` re-costed with ``FrictionParams.null()``; the realistic layer is
    ``gross`` re-costed with the measured friction. Both carry the SAME position
    fingerprint -- there is literally one series (§4)."""
    realistic = LayerReport(
        label=LABEL_REALISTIC,
        is_verdict=True,
        gross_active_ann=gross_active_ann,
        net_active_ann=apply_friction(gross_active_ann, realistic_friction),
        friction=realistic_friction,
    )
    ideal = LayerReport(
        label=LABEL_IDEAL,
        is_verdict=False,
        gross_active_ann=gross_active_ann,
        net_active_ann=apply_friction(gross_active_ann, FrictionParams.null()),
        friction=FrictionParams.null(),
    )
    hint = friction_grave_hint(
        realistic, ideal,
        strong_ideal_ann=strong_ideal_ann,
        dead_realistic_band=dead_realistic_band,
    )
    return DualLayerReport(
        realistic=realistic,
        ideal=ideal,
        shared_position_fingerprint=shared_position_fingerprint,
        friction_grave_hint=hint,
    )


def from_engine_output(
    out,
    *,
    tradability: FrictionParams | None = None,
    strong_ideal_ann: float = 0.10,
    dead_realistic_band: float = 0.0,
    active_series=None,
) -> DualLayerReport:
    """Split a committed ``EngineOutput`` into the two layers (§1b) -- the additive
    bridge to the live engine.

    The realistic friction defaults to the money-cost the harness ALREADY computed
    (``out.cost_ann`` + ``out.tax_ann``); an optional ``tradability`` overlay adds the
    fill/access dimension the harness cost model does not capture (e.g. IPO allocation
    lottery / ceiling-lock). The ideal layer zeroes all of it.

    Reads ``out`` only; mutates nothing. ``active_series`` (the harness ``active``
    daily series) is hashed for the audit fingerprint when supplied; otherwise the
    fingerprint is derived from the headline gross alone."""
    gross = out.gross_active_ann if out.gross_active_ann is not None else float("nan")
    cost = out.cost_ann if out.cost_ann is not None else 0.0
    tax = out.tax_ann if out.tax_ann is not None else 0.0
    fill = tradability.fill_fraction if tradability is not None else 1.0
    access = tradability.access_haircut_ann if tradability is not None else 0.0
    realistic_friction = FrictionParams(
        cost_ann=cost, tax_ann=tax, fill_fraction=fill, access_haircut_ann=access
    )
    fp = (
        position_fingerprint(active_series)
        if active_series is not None
        else position_fingerprint([gross])
    )
    return dual_layer_report(
        gross,
        realistic_friction,
        shared_position_fingerprint=fp,
        strong_ideal_ann=strong_ideal_ann,
        dead_realistic_band=dead_realistic_band,
    )
