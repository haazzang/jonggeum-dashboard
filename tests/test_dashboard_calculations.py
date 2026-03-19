from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import load_workbook

from dashboard_app.calculations import build_dashboard
from dashboard_app.data_loader import load_workbook_dataset
from dashboard_app.manual_metrics import ManualMetrics


ROOT = Path(__file__).resolve().parent.parent
SAMPLE_PATH = ROOT / "대시보드 AI 기초자료 만들기_sample.xlsx"


def test_sample_workbook_matches_core_dashboard_metrics():
    raw_dataset = load_workbook_dataset(SAMPLE_PATH)
    workbook = load_workbook(SAMPLE_PATH, data_only=True)
    dashboard_sheet = workbook["DASHBOARD"]

    manual_metrics = ManualMetrics(
        venture_capital_issued_note_ratio=float(dashboard_sheet["Q8"].value or 0.0),
        venture_capital_company_wide_quarter_ratio=float(dashboard_sheet["R8"].value or 0.0),
        liquidity_ratio_1m=float(dashboard_sheet["S8"].value or 0.0),
        liquidity_ratio_3m=float(dashboard_sheet["T8"].value or 0.0),
    )
    dashboard = build_dashboard(raw_dataset, manual_metrics)
    summary = dashboard["business_summary"]
    asset_sections = dashboard["asset_section"]["sections"]
    deposit_section = dashboard["deposit_section"]

    assert summary["deposits_balance"] == _approx(dashboard_sheet["E8"].value)
    assert summary["assets_yield"] == _approx(dashboard_sheet["G8"].value)
    assert summary["funding_rate"] == _approx(dashboard_sheet["H8"].value)
    assert summary["operating_margin"] == _approx(dashboard_sheet["J8"].value)
    assert dashboard["asset_section"]["total_balance"] == _approx(dashboard_sheet["F14"].value)
    assert deposit_section["total_balance"] == _approx(dashboard_sheet["P14"].value)
    assert deposit_section["personal_total"] == _approx(dashboard_sheet["Q14"].value)
    assert deposit_section["corporate_total"] == _approx(dashboard_sheet["R14"].value)
    assert deposit_section["total_rate"] == _approx(dashboard_sheet["S14"].value)

    labels = {section["label"]: section for section in asset_sections}
    assert labels["유동성자산"]["balance"] == _approx(dashboard_sheet["F15"].value)
    assert labels["기업금융관련자산"]["balance"] == _approx(dashboard_sheet["F18"].value)
    assert labels["부동산관련자산"]["balance"] == _approx(dashboard_sheet["F23"].value)
    assert labels["기타자산"]["balance"] == _approx(dashboard_sheet["F26"].value)


def _approx(value):
    return pytest.approx(float(value), rel=1e-9, abs=1e-9)
