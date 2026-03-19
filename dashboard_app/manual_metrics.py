from __future__ import annotations

import json
from dataclasses import dataclass

from dashboard_app.settings import DEFAULT_MANUAL_METRICS, MANUAL_METRICS_PATH


@dataclass(slots=True)
class ManualMetrics:
    venture_capital_issued_note_ratio: float
    venture_capital_company_wide_quarter_ratio: float
    liquidity_ratio_1m: float
    liquidity_ratio_3m: float

    def to_dict(self) -> dict[str, float]:
        return {
            "venture_capital_issued_note_ratio": self.venture_capital_issued_note_ratio,
            "venture_capital_company_wide_quarter_ratio": self.venture_capital_company_wide_quarter_ratio,
            "liquidity_ratio_1m": self.liquidity_ratio_1m,
            "liquidity_ratio_3m": self.liquidity_ratio_3m,
        }

    @classmethod
    def from_dict(cls, values: dict[str, float]) -> "ManualMetrics":
        merged = {**DEFAULT_MANUAL_METRICS, **values}
        return cls(
            venture_capital_issued_note_ratio=float(merged["venture_capital_issued_note_ratio"]),
            venture_capital_company_wide_quarter_ratio=float(
                merged["venture_capital_company_wide_quarter_ratio"]
            ),
            liquidity_ratio_1m=float(merged["liquidity_ratio_1m"]),
            liquidity_ratio_3m=float(merged["liquidity_ratio_3m"]),
        )


def load_manual_metrics(fallback: dict[str, float] | None = None) -> ManualMetrics:
    default_values = {**DEFAULT_MANUAL_METRICS, **(fallback or {})}
    if not MANUAL_METRICS_PATH.exists():
        return ManualMetrics.from_dict(default_values)

    with MANUAL_METRICS_PATH.open("r", encoding="utf-8") as file:
        persisted = json.load(file)

    return ManualMetrics.from_dict({**default_values, **persisted})


def save_manual_metrics(metrics: ManualMetrics) -> None:
    MANUAL_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANUAL_METRICS_PATH.open("w", encoding="utf-8") as file:
        json.dump(metrics.to_dict(), file, ensure_ascii=False, indent=2)
