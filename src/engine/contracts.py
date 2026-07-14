"""Typed contracts for the harness signature (Section 9).

    harness(panel, sinyal, split_spec, dial_config) -> EngineOutput

- ``Panel``       : loaded wide data frames (data_adapter output).
- ``SplitSpec``   : how the universe is split + frozen split params (Stage-0).
- ``DialConfig``  : the 8 tunable dials (Section 5); defaults = config.py (v1.1 Section 8).
- ``EngineOutput``: the Section 7 output-vector (a vector, NOT a pass/fail bit).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import pandas as pd

from . import config


class HoldPoint(StrEnum):
    """Where the prototype "holds" -> selects the split mode (Section 3.7)."""

    CROSS_SECTIONAL = "cross_sectional"
    TIMING = "timing"
    PANEL = "panel"


class SplitMode(StrEnum):
    NAME = "A"  # Mod A: name-split (cross-sectional)
    TEMPORAL = "B"  # Mod B: temporal CPCV (purge + embargo)
    PANEL = "A+B"  # combined
    TIME_HOLDOUT = "C"  # Mod C: intra-regime forward time-holdout (RR-Y1-010)


class Frequency(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"


class SortDepth(StrEnum):
    TERCILE = "tercile"
    TOPN = "topN"
    DECILE = "decile"


class NameSplitMethod(StrEnum):
    """How Mod-A partitions the universe into arms (Section 3.2). Alphabetical/
    ordered assignment is FORBIDDEN -- both options below are balance-preserving."""

    LIQUIDITY = "liquidity"  # default: ADV-stratified pair-randomization (equal liquidity/arm)
    RANDOM = "random"  # plain seed-fixed random halves


class RegimeTarget(StrEnum):
    REGIME_R = "regime_R"
    AGNOSTIC = "agnostic"


class ReturnBasis(StrEnum):
    TR_GROSS = "tr_index_gross"
    TR_NET = "tr_index_net"


class CutPolicy(StrEnum):
    ANCHORED = "anchored"
    ROLLING = "rolling"
    EXPANDING = "expanding"


class AgreementConfidence(StrEnum):
    """Trustworthiness qualifier on the Mod-A conjugate verdict (RR-Y1-009).

    Additive ONLY: orthogonal to ``agreement_pass`` and the three keep-bar
    conditions (DEC-049 untouched). It annotates whether the preconditions for a
    trustworthy conjugate measurement held -- never makes a factor pass/fail.
    """

    HIGH = "high"  # adequate breadth + adequate R + no confounded trigger
    LOW = "low"  # underpowered: per-arm names or effective R below a frozen floor
    CONFOUNDED = "confounded"  # shared-factor flag OR single-regime eval window
    # RR-Y1-028 (D1d): the Mod-A leg never RAN (degenerate universe -- e.g. too few
    # eligible names to form two arms). This is NOT a graded measurement; it is the
    # ABSENCE of one. Kept distinct from LOW (an underpowered but real measurement)
    # so a consumer can never read "could not measure" as "measured and failed".
    # "Not detected" is not "does not exist" (ADR-0007).
    NOT_MEASURED = "not_measured"


class HoldoutConfidence(StrEnum):
    """Trustworthiness qualifier on the Mod-C intra-regime time-holdout verdict (RR-Y1-010).

    Additive ONLY: orthogonal to ``holdout_persistence_pass`` -- it annotates whether
    the preconditions for a trustworthy forward-persistence read held, never makes a
    factor pass/fail. Deliberately a SEPARATE enum from ``AgreementConfidence`` because
    the regime semantics are OPPOSITE-but-consistent across the two modes:

    - Mod-A (``AgreementConfidence``): a single-regime eval window is SUSPECT -- a
      within-regime common-factor artifact can fake a clean conjugate PASS.
    - Mod-C (this enum): single-regime is the DESIGN, not a confound (the question is
      precisely "does it persist forward WITHIN one regime"). The confound here is the
      holdout window CROSSING ``REGIME_SPLIT`` -- if train sits in one regime and the
      holdout spills into another, the same-regime-persistence question is polluted.
    """

    HIGH = "high"  # adequate holdout breadth + no confounded trigger
    LOW = "low"  # underpowered: holdout IC observations below a frozen floor
    CONFOUNDED = "confounded"  # holdout crosses REGIME_SPLIT OR shared-factor flag on the holdout


@dataclass(frozen=True, eq=False)
class Panel:
    """Loaded data panel. All frames are wide: index=date, columns=symbol.

    ``eq=False`` because DataFrame ``__eq__`` is element-wise (an auto-generated
    ``__eq__`` would raise "ambiguous truth value").
    """

    close: pd.DataFrame  # adjusted_close
    tr_gross: pd.DataFrame  # tr_index_gross (total-return, dividends reinvested)
    tr_net: pd.DataFrame  # tr_index_net
    value_tl: pd.DataFrame  # daily traded value (liquidity proxy)
    membership: dict[str, pd.DataFrame]  # {"bist100": 0/1 flags, "bist30": ...} PIT
    market: pd.Series  # market index level (xu100); returns = pct_change
    tufe: pd.Series  # CPI level
    tlref: pd.Series  # TLREF
    frequency: Frequency = Frequency.DAILY

    @property
    def dates(self) -> pd.DatetimeIndex:
        return self.close.index  # type: ignore[return-value]

    @property
    def names(self) -> list[str]:
        return list(self.close.columns)


@dataclass(frozen=True)
class SplitSpec:
    """Split structure frozen at Stage-0 (dials 2, 4, 8). Section 3."""

    split_mode: SplitMode
    frequency: Frequency
    embargo_h: int = 1  # = signal construction-window (Section 3.4); h >= 1
    R: int = config.SPLIT_R_MIN  # seed-fixed name-splits (Mod-A)
    seed: int = 0
    cpcv_n: int = config.CPCV_DAILY_N  # Mod-B temporal CPCV blocks
    cpcv_k: int = config.CPCV_DAILY_K
    # The Mod-A eligibility floor.
    #
    # RR-Y1-028 (D1b) replaced LIQUID_ADV_MIN_TL (1e7 -- a capacity constraint this operator does
    # not have, which left 38 eligible names against the 100 needed) with a tradability-anchored
    # bar. RR-Y1-030 keeps that bar but changes its DENOMINATION: it is now stated in BASE-DATE TL
    # and CPI-indexed forward to each decision date
    #     floor(t) = split_arm_floor_tl * TUFE(t) / TUFE(ELIGIBLE_ADV_FLOOR_BASE_DATE)
    # because the previous end-of-window denomination required TUFE(d1) -- the future -- merely to
    # express the threshold, which was a look-ahead in its own right.
    #
    # The REAL bar is unchanged (227,611 base-date TL == 2.0M end-of-window TL == the same 1%-of-a
    # -day's-turnover tradability anchor). Stage-0 records this value in its `split_arm_floor`
    # field, so any run's universe bar stays auditable.
    # NOTE: LIQUID_ADV_MIN_TL itself is UNCHANGED and still governs data_adapter.liquid_names.
    split_arm_floor_tl: float = config.ELIGIBLE_ADV_FLOOR_BASE_TL
    sort_depth: SortDepth = SortDepth.TERCILE
    min_names_per_arm: int = config.MIN_NAMES_PER_ARM
    name_split_method: NameSplitMethod = NameSplitMethod.LIQUIDITY  # Mod-A only (Section 3.2)
    holdout_start: str | None = None  # Mod-C boundary (ISO date); train < (this - embargo), holdout >= this

    def __post_init__(self) -> None:
        if self.embargo_h < 1:
            raise ValueError(f"embargo_h must be >= 1 (got {self.embargo_h})")
        if self.cpcv_k >= self.cpcv_n:
            raise ValueError(f"cpcv_k ({self.cpcv_k}) must be < cpcv_n ({self.cpcv_n})")
        if self.R < 1:
            raise ValueError(f"R must be >= 1 (got {self.R})")
        if self.split_mode is SplitMode.TIME_HOLDOUT and self.holdout_start is None:
            raise ValueError(
                "split_mode C (TIME_HOLDOUT) requires holdout_start (the pre-registered "
                "train/holdout boundary date); none was given."
            )
        # Section 3.6 / 8: monthly temporal-CPCV is power-poor -> Mod-A mandatory.
        if (
            config.MONTHLY_TEMPORAL_CPCV_FORBIDDEN
            and self.frequency is Frequency.MONTHLY
            and self.split_mode is not SplitMode.NAME
        ):
            raise ValueError(
                "monthly frequency requires split_mode A (name-split); "
                "temporal-CPCV is power-poor at monthly frequency (Section 3.6)."
            )


@dataclass(frozen=True)
class DialConfig:
    """The 8 tunable dials (Section 5). Defaults = frozen v1.1 Section 8.

    Dials 2 (split-mode), 4 (embargo) and 8 (arm-floor + sort-depth) live in
    ``SplitSpec`` (they are split structure); the rest live here.
    """

    psi: str = config.IC_TYPE  # dial 1
    neutralization: tuple[str, ...] = config.NEUTRALIZATION_FACTORS_DEFAULT  # dial 3
    return_basis: ReturnBasis = ReturnBasis.TR_GROSS
    cut_policies: tuple[CutPolicy, ...] = (
        CutPolicy.ANCHORED,
        CutPolicy.ROLLING,
        CutPolicy.EXPANDING,
    )  # dial 7
    use_pbo: bool = True  # dial 5
    use_dsr: bool = True  # dial 6
    nw_lag: int | None = None  # resolved from frequency when None
    winsorize: tuple[float, float] = (config.WINSORIZE_LOWER, config.WINSORIZE_UPPER)
    beta_window: int = config.BETA_WINDOW_DAYS
    agreement_t_min: float = config.AGREEMENT_CROSS_IC_T_MIN
    sign_consistency_min: float = config.SIGN_CONSISTENCY_MIN
    pbo_max: float = config.PBO_THRESHOLD
    dsr_min: float = config.DSR_MIN
    residual_corr_null_pctile: int = config.RESIDUAL_CORR_NULL_PCTILE

    def __post_init__(self) -> None:
        if not self.neutralization:
            raise ValueError("neutralization must list >= 1 factor (market is the minimum)")
        unknown = set(self.neutralization) - config.ALLOWED_FACTORS
        if unknown:
            raise ValueError(f"unknown neutralization factor(s): {sorted(unknown)}")
        lo, hi = self.winsorize
        if not (0.0 <= lo < hi <= 1.0):
            raise ValueError(f"winsorize bounds invalid: {self.winsorize}")

    def nw_lag_for(self, frequency: Frequency, h: int = 1) -> int:
        """HAC bandwidth for a return series sampled at ``frequency``.

        RR-Y1-028 (D2): ``h`` is the signal's construction window. When the engine scores a
        signal against an h-day FORWARD return sampled every day, consecutive observations
        overlap by h-1 days, and a HAC bandwidth below h cannot absorb that induced
        autocorrelation -- the t-stat comes out too large. So the daily default widens to
        ``max(NW_LAG_DAILY, h)``.

        ``h`` defaults to 1 so existing callers that pass only ``frequency`` (Mod-A/B/C)
        are byte-unchanged. An explicitly set ``nw_lag`` always wins (examples/rry1008
        already passed ``nw_lag=21`` by hand for exactly this reason).
        """
        if self.nw_lag is not None:
            return self.nw_lag
        if frequency is Frequency.DAILY:
            return max(config.NW_LAG_DAILY, int(h))
        return config.NW_LAG_MONTHLY

    def requires_market_neutralization(self, split_mode: SplitMode) -> None:
        """Section 3.5: market-beta neutralization is mandatory for Mod-A."""
        if split_mode in (SplitMode.NAME, SplitMode.PANEL) and "market" not in self.neutralization:
            raise ValueError(
                "Mod-A (name-split) requires at least market-beta neutralization "
                "(Section 3.5); add 'market' to dial_config.neutralization."
            )


@dataclass
class EngineOutput:
    """Section 7 output-vector. Populated incrementally across Faz-1..3; every
    field defaults to None/empty so a partial run is still a valid object."""

    # returns -- total-return based (bullets 1-2)
    gross_active_ann: float | None = None
    net_active_ann: float | None = None
    cost_ann: float | None = None
    tax_ann: float | None = None
    mean_rt_bps: float | None = None
    # fair-null + mirror (bullet 3)
    null_percentile: float | None = None
    mirror_active_ann: float | None = None
    # relative benchmark (bullet 4): the strategy's TOTAL return vs max(TUFE, TLREF)
    #
    # RR-Y1-028 (D3): ``beats_benchmark_floor`` is now decided on the strategy's TOTAL
    # nominal return (``benchmark_ew_ann + net_active_ann``) against the NOMINAL floor.
    # It used to deflate the ACTIVE spread and compare that REAL number to a NOMINAL floor,
    # which demanded a tilt beat its own EW benchmark by more than inflation.
    #
    # ``real_active_ann`` is RETAINED (committed field; the PEAD engine output carries it)
    # and still means "the TUFE-deflated ACTIVE spread" -- but it is DESCRIPTIVE ONLY and is
    # no longer what the gate judges. Read ``real_total_ann`` for the adjudicated quantity.
    real_active_ann: float | None = None  # descriptive; NOT the gate (see D3)
    real_total_ann: float | None = None  # NEW: TUFE-deflated TOTAL return -- the gate's subject
    benchmark_ew_ann: float | None = None  # NEW: nominal return of the EW-universe benchmark
    strategy_total_ann: float | None = None  # NEW: nominal benchmark_ew_ann + net_active_ann
    benchmark_floor_ann: float | None = None  # nominal max(TUFE, TLREF)
    benchmark_floor_real_ann: float | None = None  # NEW: the same floor, deflated
    beats_benchmark_floor: bool | None = None
    # significance (bullet 5): PBO, cut-family deflated OOS-t, DSR
    pbo: float | None = None
    deflated_oos_t: float | None = None
    dsr: float | None = None
    dsr_n_trials: int | None = None  # honest tried-config count fed to the DSR deflation (FAZ-4 (b))
    nw_t: float | None = None
    # conjugate agreement + residual corr (bullet 6; Section 4.1/4.2 -- kept SEPARATE)
    #
    # RR-Y1-028 (D1d) -- READ THIS BEFORE ADJUDICATING:
    # ``agreement_pass`` is TRI-STATE and always was (``bool | None``):
    #   True  -> Mod-A ran and the 3-part bar was cleared
    #   False -> Mod-A ran and the bar was NOT cleared      (a real negative)
    #   None  -> Mod-A did NOT run                          (NO measurement exists)
    # Before RR-Y1-028 the degenerate-universe guard wrote ``False`` here, so a leg
    # that never executed was indistinguishable from one that executed and failed --
    # and every keep-bar consumer counted it as a failure. Use ``agreement_measured``
    # (and ``pbo_measured``) to tell the two apart; ``src/engine/keep_bar.py`` does
    # this for you. Same tri-state semantics apply to ``pbo``.
    agreement_pass: bool | None = None
    agreement_measured: bool | None = None  # False -> the Mod-A leg never ran (NOT a failure)
    pbo_measured: bool | None = None  # False -> no real CSCV PBO exists for this run
    agreement_t_cross_median: float | None = None  # min over both directions
    sign_consistency: float | None = None
    residual_cross_sectional_corr: float | None = None
    residual_corr_flag: bool | None = None  # red flag if > null pctile
    # verdict-confidence qualifier (RR-Y1-009; additive, orthogonal to agreement_pass)
    agreement_confidence: AgreementConfidence | None = None
    agreement_confidence_reasons: tuple[str, ...] = ()
    # intra-regime forward time-holdout (Mod-C; RR-Y1-010; additive, only on TIME_HOLDOUT runs)
    holdout_persistence_pass: bool | None = None
    holdout_ic_t: float | None = None
    holdout_ic_mean: float | None = None
    train_ic_t: float | None = None
    train_ic_mean: float | None = None
    holdout_sign_consistent: bool | None = None
    n_holdout_obs: int | None = None
    n_train_obs: int | None = None
    holdout_confidence: HoldoutConfidence | None = None
    holdout_confidence_reasons: tuple[str, ...] = ()
    # per-regime breakdown (bullet 7; manual label)
    per_regime: dict[str, dict[str, float]] = field(default_factory=dict)
    # parameter plateau / sensitivity (bullet 8)
    plateau_map: dict[str, float] = field(default_factory=dict)
    # PM-1 + guards (Section 10)
    pm1_guard_raised: bool = False
    guard_messages: tuple[str, ...] = ()
    # provenance
    n_obs: int | None = None
    n_names: int | None = None
    split_mode: str | None = None
    notes: tuple[str, ...] = ()
