from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
MANUAL_METRICS_PATH = DATA_DIR / "manual_metrics.json"

UNIT_EOK = 100_000_000
OTHER_EXPENSE_RATE = 0.002

WORKBOOK_SHEETS = {
    "dashboard": ("DASHBOARD",),
    "deposits": ("1. 수신잔고", "1.수신잔고"),
    "assets": ("2. 운용자산", "2.운용자산"),
    "daily_trend": (
        "3. 일별잔고추이",
        "3. 일별 잔고 추이",
        "3.일별잔고추이",
        "3.일별 잔고 추이",
    ),
}

DEFAULT_MANUAL_METRICS = {
    "venture_capital_issued_note_ratio": 0.0,
    "venture_capital_company_wide_quarter_ratio": 0.8209,
    "liquidity_ratio_1m": 6.0407,
    "liquidity_ratio_3m": 5.5094,
}

ASSET_GROUPS = (
    {
        "key": "liquidity_assets",
        "label": "유동성자산",
        "children": (
            {
                "key": "cash_equivalents",
                "label": "현금성자산",
                "filter": "유동성자산현금성자산",
                "yield_override": 0.025,
                "excel_duration_override": 0.0027397260273972603,
            },
            {
                "key": "other_liquidity",
                "label": "기타유동성자산",
                "filter": "유동성자산기타유동성자산",
                "yield_override": 0.0,
                "excel_duration_override": 0.0,
            },
        ),
    },
    {
        "key": "corporate_finance_assets",
        "label": "기업금융관련자산",
        "children": (
            {"key": "corporate_cp_stb", "label": "CP/STB", "filter": "기업금융관련자산CP/STB"},
            {"key": "corporate_bonds", "label": "채권", "filter": "기업금융관련자산채권"},
            {"key": "corporate_loans", "label": "기업대출", "filter": "기업금융관련자산기업대출"},
            {"key": "corporate_equity", "label": "출자", "filter": "기업금융관련자산출자"},
        ),
    },
    {
        "key": "real_estate_assets",
        "label": "부동산관련자산",
        "children": (
            {"key": "securitized_real_estate", "label": "유동화증권", "filter": "부동산관련자산유동화증권"},
            {"key": "direct_real_estate", "label": "부동산", "filter": "부동산관련자산부동산"},
        ),
    },
    {
        "key": "other_assets",
        "label": "기타자산",
        "children": (
            {"key": "other_cp_stb", "label": "CP/STB", "filter": "기타자산CP/STB"},
            {"key": "other_bonds", "label": "채권", "filter": "기타자산채권"},
            {"key": "other_equity", "label": "출자", "filter": "기타자산출자"},
        ),
    },
)

DEPOSIT_BUCKETS = (
    {
        "key": "demand",
        "row_label": "수시형",
        "term_label": "수시형(1일~365일)",
        "filter1_personal": "개인수시형(1일~365일)",
        "filter1_corporate": "법인수시형(1일~365일)",
    },
    {
        "key": "term_7_30",
        "row_label": "(7일~30일)",
        "term_label": "약정형(7일~30일)",
        "filter1_personal": "개인약정형(7일~30일)",
        "filter1_corporate": "법인약정형(7일~30일)",
    },
    {
        "key": "term_31_90",
        "row_label": "(31일~90일)",
        "term_label": "약정형(31일~90일)",
        "filter1_personal": "개인약정형(31일~90일)",
        "filter1_corporate": "법인약정형(31일~90일)",
    },
    {
        "key": "term_91_180",
        "row_label": "(91일~180일)",
        "term_label": "약정형(91일~180일)",
        "filter1_personal": "개인약정형(91일~180일)",
        "filter1_corporate": "법인약정형(91일~180일)",
    },
    {
        "key": "term_181_270",
        "row_label": "(181일~270일)",
        "term_label": "약정형(181일~270일)",
        "filter1_personal": "개인약정형(181일~270일)",
        "filter1_corporate": "법인약정형(181일~270일)",
    },
    {
        "key": "term_271_364",
        "row_label": "(271일~364일)",
        "term_label": "약정형(271일~364일)",
        "filter1_personal": "개인약정형(271일~364일)",
        "filter1_corporate": "법인약정형(271일~364일)",
    },
    {
        "key": "term_365",
        "row_label": "(365일)",
        "term_label": "약정형(365일)",
        "filter1_personal": "개인약정형(365일)",
        "filter1_corporate": "법인약정형(365일)",
    },
)
