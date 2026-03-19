from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from dashboard_app.data_loader import RawDataset
from dashboard_app.manual_metrics import ManualMetrics
from dashboard_app.settings import ASSET_GROUPS, ASSET_VERSION, DEPOSIT_BUCKETS, OTHER_EXPENSE_RATE, UNIT_EOK


def build_dashboard(raw_dataset: RawDataset, manual_metrics: ManualMetrics) -> dict[str, Any]:
    deposits = raw_dataset.deposits.copy()
    assets = raw_dataset.assets.copy()

    deposit_details = deposits.loc[~deposits["dashboard_is_summary"]].copy()

    asset_sections = _build_asset_sections(assets)
    deposit_section = _build_deposit_section(deposit_details)

    total_assets_balance = asset_sections["total_balance"]
    total_assets_yield = asset_sections["total_yield"]
    total_assets_excel_duration = asset_sections["total_excel_duration"]
    total_assets_corrected_duration = asset_sections["total_corrected_duration"]

    total_deposits_balance = deposit_section["total_balance"]
    total_funding_rate = deposit_section["total_rate"]
    operating_margin = total_assets_yield - total_funding_rate - OTHER_EXPENSE_RATE

    regulatory_metrics = _build_regulatory_metrics(
        asset_sections=asset_sections,
        total_assets_balance=total_assets_balance,
        manual_metrics=manual_metrics,
    )

    source = raw_dataset.source
    base_date = _format_date(raw_dataset.base_date)

    deposit_preview = _preview_table(
        deposit_details,
        columns=("기준일자", "상품구분", "필터1", "필터2", "발행잔고", "조달금리"),
    )
    asset_preview = _preview_table(
        assets,
        columns=("편입일자", "만기일자", "자산명", "필터", "BS금액", "운용금리(%)", "듀레이션"),
    )
    trend_chart = _build_trend_chart(raw_dataset.daily_trend, raw_dataset.base_date)

    data_quality = {
        "deposit_rows": len(deposit_details),
        "asset_rows": len(assets),
        "deposit_missing_filters": int(
            deposit_details["dashboard_filter2"].isna().sum() + deposit_details["dashboard_filter1"].isna().sum()
        ),
        "asset_missing_filters": int(assets["dashboard_filter"].isna().sum()),
        "deposit_missing_balance": int(deposit_details["dashboard_balance"].isna().sum()),
        "asset_missing_balance": int(assets["dashboard_balance"].isna().sum()),
        "trend_series": trend_chart["series_count"],
        "trend_days": trend_chart["date_count"],
    }

    return {
        "title": "종금 영업 대시보드",
        "asset_version": ASSET_VERSION,
        "base_date": base_date,
        "source": {
            "label": source.label,
            "kind": source.kind,
            "modified_at": _format_datetime(source.modified_at),
            "path": str(source.workbook_path or source.deposits_csv_path.parent),
        },
        "summary_cards": [
            {
                "label": "수신 말잔",
                "value": _format_amount(total_deposits_balance),
                "unit": "억원",
                "detail": f"개인 {_format_amount(deposit_section['personal_total'])} / 법인 {_format_amount(deposit_section['corporate_total'])}",
            },
            {
                "label": "운용수익률",
                "value": _format_percent(total_assets_yield),
                "unit": "",
                "detail": f"운용자산 말잔 {_format_amount(total_assets_balance)}억원",
            },
            {
                "label": "조달금리",
                "value": _format_percent(total_funding_rate),
                "unit": "",
                "detail": f"기타비용 {_format_percent(OTHER_EXPENSE_RATE)} 반영 전",
            },
            {
                "label": "영업수지",
                "value": _format_percent(operating_margin),
                "unit": "",
                "detail": "운용수익률 - 조달금리 - 기타비용",
            },
        ],
        "business_summary": {
            "deposits_balance": total_deposits_balance,
            "assets_balance": total_assets_balance,
            "assets_yield": total_assets_yield,
            "funding_rate": total_funding_rate,
            "other_expense_rate": OTHER_EXPENSE_RATE,
            "operating_margin": operating_margin,
        },
        "asset_section": asset_sections,
        "deposit_section": deposit_section,
        "regulatory_metrics": regulatory_metrics,
        "duration_correction": {
            "excel_duration": total_assets_excel_duration,
            "corrected_duration": total_assets_corrected_duration,
            "gap": total_assets_excel_duration - total_assets_corrected_duration,
            "excel_duration_display": _format_number(total_assets_excel_duration),
            "corrected_duration_display": _format_number(total_assets_corrected_duration),
            "gap_display": _format_number(total_assets_excel_duration - total_assets_corrected_duration),
            "note": "원본 엑셀 Duration 수식은 운용금리를 다시 참조합니다. 보정 듀레이션은 raw 시트의 듀레이션 컬럼으로 재계산했습니다.",
        },
        "trend_chart": trend_chart,
        "mix_bars": _build_mix_bars(asset_sections),
        "maturity_bars": _build_maturity_bars(deposit_section),
        "data_quality": data_quality,
        "manual_metrics_form": {
            "venture_capital_issued_note_ratio": _format_number(
                manual_metrics.venture_capital_issued_note_ratio * 100
            ),
            "venture_capital_company_wide_quarter_ratio": _format_number(
                manual_metrics.venture_capital_company_wide_quarter_ratio * 100
            ),
            "liquidity_ratio_1m": _format_number(manual_metrics.liquidity_ratio_1m * 100),
            "liquidity_ratio_3m": _format_number(manual_metrics.liquidity_ratio_3m * 100),
        },
        "raw_tables": {
            "deposits": deposit_preview,
            "assets": asset_preview,
        },
    }


def _build_asset_sections(assets: pd.DataFrame) -> dict[str, Any]:
    sections = []
    total_balance_raw = 0.0
    total_yield_weighted = 0.0
    total_excel_duration_weighted = 0.0
    total_corrected_duration_weighted = 0.0

    for group in ASSET_GROUPS:
        children = []
        group_balance_raw = 0.0
        group_yield_weighted = 0.0
        group_excel_duration_weighted = 0.0
        group_corrected_duration_weighted = 0.0

        for child in group["children"]:
            subset = assets.loc[assets["dashboard_filter"] == child["filter"]].copy()
            balance_raw = float(subset["dashboard_balance"].sum())
            yield_rate = child.get("yield_override")
            if yield_rate is None:
                yield_rate = _weighted_average(
                    subset["dashboard_rate"], subset["dashboard_balance"], divisor=100.0
                )

            excel_duration = child.get("excel_duration_override")
            if excel_duration is None:
                excel_duration = _weighted_average(subset["dashboard_rate"], subset["dashboard_balance"])
            corrected_duration = _weighted_average(
                subset["dashboard_duration"], subset["dashboard_balance"]
            )

            group_balance_raw += balance_raw
            group_yield_weighted += balance_raw * yield_rate
            group_excel_duration_weighted += balance_raw * excel_duration
            group_corrected_duration_weighted += balance_raw * corrected_duration

            children.append(
                {
                    "label": child["label"],
                    "balance": balance_raw / UNIT_EOK,
                    "yield": yield_rate,
                    "excel_duration": excel_duration,
                    "corrected_duration": corrected_duration,
                    "display_balance": _format_amount(balance_raw / UNIT_EOK),
                    "display_yield": _format_percent(yield_rate),
                    "display_excel_duration": _format_number(excel_duration),
                    "display_corrected_duration": _format_number(corrected_duration),
                }
            )

        group_yield = group_yield_weighted / group_balance_raw if group_balance_raw else 0.0
        group_excel_duration = (
            group_excel_duration_weighted / group_balance_raw if group_balance_raw else 0.0
        )
        group_corrected_duration = (
            group_corrected_duration_weighted / group_balance_raw if group_balance_raw else 0.0
        )

        total_balance_raw += group_balance_raw
        total_yield_weighted += group_balance_raw * group_yield
        total_excel_duration_weighted += group_balance_raw * group_excel_duration
        total_corrected_duration_weighted += group_balance_raw * group_corrected_duration

        sections.append(
            {
                "key": group["key"],
                "label": group["label"],
                "balance": group_balance_raw / UNIT_EOK,
                "yield": group_yield,
                "excel_duration": group_excel_duration,
                "corrected_duration": group_corrected_duration,
                "display_balance": _format_amount(group_balance_raw / UNIT_EOK),
                "display_yield": _format_percent(group_yield),
                "display_excel_duration": _format_number(group_excel_duration),
                "display_corrected_duration": _format_number(group_corrected_duration),
                "children": children,
            }
        )

    total_yield = total_yield_weighted / total_balance_raw if total_balance_raw else 0.0
    total_excel_duration = (
        total_excel_duration_weighted / total_balance_raw if total_balance_raw else 0.0
    )
    total_corrected_duration = (
        total_corrected_duration_weighted / total_balance_raw if total_balance_raw else 0.0
    )

    return {
        "sections": sections,
        "total_balance": total_balance_raw / UNIT_EOK,
        "total_yield": total_yield,
        "total_excel_duration": total_excel_duration,
        "total_corrected_duration": total_corrected_duration,
        "display_total_balance": _format_amount(total_balance_raw / UNIT_EOK),
        "display_total_yield": _format_percent(total_yield),
        "display_total_excel_duration": _format_number(total_excel_duration),
        "display_total_corrected_duration": _format_number(total_corrected_duration),
    }


def _build_deposit_section(deposits: pd.DataFrame) -> dict[str, Any]:
    rows = []
    demand_bucket = DEPOSIT_BUCKETS[0]
    demand_row = _build_deposit_row(deposits, demand_bucket)
    rows.append(demand_row)

    term_rows = [_build_deposit_row(deposits, bucket) for bucket in DEPOSIT_BUCKETS[1:]]
    term_total_balance = sum(row["balance"] for row in term_rows)
    term_personal_total = sum(row["personal"] for row in term_rows)
    term_corporate_total = sum(row["corporate"] for row in term_rows)
    term_rate = _weighted_average(
        [row["rate"] for row in term_rows],
        [row["balance"] for row in term_rows],
    )

    total_balance = demand_row["balance"] + term_total_balance
    total_personal = demand_row["personal"] + term_personal_total
    total_corporate = demand_row["corporate"] + term_corporate_total
    total_rate = _weighted_average(
        [demand_row["rate"], term_rate],
        [demand_row["balance"], term_total_balance],
    )

    return {
        "demand_row": demand_row,
        "term_rows": term_rows,
        "term_total_balance": term_total_balance,
        "term_total_rate": term_rate,
        "total_balance": total_balance,
        "personal_total": total_personal,
        "corporate_total": total_corporate,
        "total_rate": total_rate,
        "display_total_balance": _format_amount(total_balance),
        "display_personal_total": _format_amount(total_personal),
        "display_corporate_total": _format_amount(total_corporate),
        "display_total_rate": _format_percent(total_rate),
        "display_term_total_balance": _format_amount(term_total_balance),
        "display_term_total_rate": _format_percent(term_rate),
        "rows": rows + term_rows,
    }


def _build_deposit_row(deposits: pd.DataFrame, bucket: dict[str, str]) -> dict[str, Any]:
    term_subset = deposits.loc[deposits["dashboard_filter2"] == bucket["term_label"]]
    personal_subset = deposits.loc[deposits["dashboard_filter1"] == bucket["filter1_personal"]]
    corporate_subset = deposits.loc[deposits["dashboard_filter1"] == bucket["filter1_corporate"]]

    balance = float(term_subset["dashboard_balance"].sum() / UNIT_EOK)
    personal = float(personal_subset["dashboard_balance"].sum() / UNIT_EOK)
    corporate = float(corporate_subset["dashboard_balance"].sum() / UNIT_EOK)
    rate = _weighted_average(term_subset["dashboard_rate"], term_subset["dashboard_balance"], divisor=100.0)

    return {
        "key": bucket["key"],
        "label": bucket["row_label"],
        "term_label": bucket["term_label"],
        "balance": balance,
        "personal": personal,
        "corporate": corporate,
        "rate": rate,
        "display_balance": _format_amount(balance),
        "display_personal": _format_amount(personal),
        "display_corporate": _format_amount(corporate),
        "display_rate": _format_percent(rate),
    }


def _build_regulatory_metrics(
    asset_sections: dict[str, Any],
    total_assets_balance: float,
    manual_metrics: ManualMetrics,
) -> list[dict[str, Any]]:
    sections_by_label = {section["label"]: section for section in asset_sections["sections"]}

    corporate_ratio = (
        sections_by_label["기업금융관련자산"]["balance"] / total_assets_balance if total_assets_balance else 0.0
    )
    real_estate_ratio = (
        sections_by_label["부동산관련자산"]["balance"] / total_assets_balance if total_assets_balance else 0.0
    )

    return [
        _reg_metric("기업금융관련자산 비율", corporate_ratio, 0.30, "gte"),
        _reg_metric("부동산관련자산 비율", real_estate_ratio, 0.10, "lte"),
        _reg_metric(
            "모험자본 비율(전사 분기)",
            manual_metrics.venture_capital_company_wide_quarter_ratio,
            0.25,
            "gte",
            secondary=f"발행어음 {_format_percent(manual_metrics.venture_capital_issued_note_ratio)}",
        ),
        _reg_metric("유동성비율 1개월", manual_metrics.liquidity_ratio_1m, 1.0, "gte"),
        _reg_metric("유동성비율 3개월", manual_metrics.liquidity_ratio_3m, 1.0, "gte"),
    ]


def _build_mix_bars(asset_sections: dict[str, Any]) -> list[dict[str, Any]]:
    total = asset_sections["total_balance"] or 1.0
    bars = []
    for section in asset_sections["sections"]:
        share = section["balance"] / total if total else 0.0
        bars.append(
            {
                "label": section["label"],
                "share": share,
                "share_display": _format_percent(share),
                "value_display": section["display_balance"],
            }
        )
    return bars


def _build_trend_chart(daily_trend: pd.DataFrame, base_date: datetime | None = None) -> dict[str, Any]:
    if daily_trend.empty:
        return {
            "available": False,
            "message": "업로드한 원본에 `3. 일별잔고추이` 시트가 없어서 차트를 표시하지 않습니다.",
            "labels": [],
            "series": {},
            "series_order": [],
            "featured_keys": [],
            "default_key": None,
            "date_count": 0,
            "series_count": 0,
            "period_label": "-",
        }

    date_columns = [column for column in daily_trend.columns if _is_trend_date_column(column)]
    date_columns = _trim_trend_date_columns(daily_trend, date_columns, base_date)
    if not date_columns:
        return {
            "available": False,
            "message": "`3. 일별잔고추이` 시트에서 날짜 컬럼을 찾지 못했습니다.",
            "labels": [],
            "series": {},
            "series_order": [],
            "featured_keys": [],
            "default_key": None,
            "date_count": 0,
            "series_count": 0,
            "period_label": "-",
        }

    series: dict[str, dict[str, Any]] = {}
    series_order: list[dict[str, Any]] = []
    for record in daily_trend.to_dict("records"):
        key = str(record.get("series_key") or "").strip()
        if not key:
            continue

        values = [_to_eok_amount(record.get(date_column)) for date_column in date_columns]
        if not any(value is not None for value in values):
            continue

        path = str(record.get("series_path") or key)
        label = str(record.get("series_label") or path)
        depth = int(record.get("depth") or 1)
        group = str(record.get("level_1") or label)
        item = {
            "key": key,
            "label": label,
            "path": path,
            "group": group,
            "depth": depth,
            "values": values,
        }
        series[key] = item
        series_order.append(
            {
                "key": key,
                "label": label,
                "path": path,
                "group": group,
                "depth": depth,
            }
        )

    if not series_order:
        return {
            "available": False,
            "message": "`3. 일별잔고추이` 시트에 차트로 그릴 수 있는 값이 없습니다.",
            "labels": [],
            "series": {},
            "series_order": [],
            "featured_keys": [],
            "default_key": None,
            "date_count": 0,
            "series_count": 0,
            "period_label": "-",
        }

    featured_candidates = (
        "수신잔고",
        "운용자산",
        "운용자산 > 유동성자산",
        "운용자산 > 기업금융관련자산",
        "운용자산 > 부동산관련자산",
        "운용자산 > 기타자산",
        "수신잔고 > 수시형",
        "수신잔고 > 약정형",
    )
    featured_keys = [candidate for candidate in featured_candidates if candidate in series]
    if not featured_keys:
        featured_keys = [item["key"] for item in series_order[:6]]

    default_key = "수신잔고" if "수신잔고" in series else featured_keys[0]

    return {
        "available": True,
        "message": None,
        "labels": date_columns,
        "series": series,
        "series_order": series_order,
        "featured_keys": featured_keys,
        "default_key": default_key,
        "date_count": len(date_columns),
        "series_count": len(series_order),
        "period_label": f"{date_columns[0]} ~ {date_columns[-1]}",
    }


def _build_maturity_bars(deposit_section: dict[str, Any]) -> list[dict[str, Any]]:
    total = deposit_section["total_balance"] or 1.0
    bars = []
    for row in deposit_section["rows"]:
        bars.append(
            {
                "label": row["label"],
                "balance": row["balance"],
                "share": row["balance"] / total if total else 0.0,
                "personal_share": row["personal"] / row["balance"] if row["balance"] else 0.0,
                "corporate_share": row["corporate"] / row["balance"] if row["balance"] else 0.0,
                "balance_display": row["display_balance"],
            }
        )
    return bars


def _preview_table(dataframe: pd.DataFrame, columns: tuple[str, ...]) -> dict[str, Any]:
    preview_columns = [column for column in columns if column in dataframe.columns]
    preview_frame = dataframe[preview_columns].copy()
    preview_frame = preview_frame.fillna("")
    preview_records = []
    for _, row in preview_frame.iterrows():
        preview_records.append([_preview_value(row[column]) for column in preview_columns])
    return {"columns": preview_columns, "rows": preview_records}


def _is_trend_date_column(value: object) -> bool:
    try:
        datetime.strptime(str(value), "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _trim_trend_date_columns(
    daily_trend: pd.DataFrame,
    date_columns: list[str],
    base_date: datetime | None,
) -> list[str]:
    if not date_columns:
        return date_columns

    if base_date is not None:
        cutoff = base_date.strftime("%Y-%m-%d")
        trimmed = [column for column in date_columns if column <= cutoff]
        if trimmed:
            date_columns = trimmed

    last_signal_index = len(date_columns) - 1
    for index in range(len(date_columns) - 1, -1, -1):
        series = pd.to_numeric(daily_trend[date_columns[index]], errors="coerce").fillna(0.0)
        if float(series.abs().sum()) > 0:
            last_signal_index = index
            break
    return date_columns[: last_signal_index + 1]


def _to_eok_amount(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value) / UNIT_EOK


def _weighted_average(values, weights, divisor: float = 1.0) -> float:
    values_series = pd.to_numeric(pd.Series(values), errors="coerce").fillna(0.0)
    weights_series = pd.to_numeric(pd.Series(weights), errors="coerce").fillna(0.0)
    total_weight = float(weights_series.sum())
    if total_weight == 0:
        return 0.0
    return float((values_series * weights_series).sum() / total_weight / divisor)


def _reg_metric(
    label: str,
    value: float,
    threshold: float,
    comparator: str,
    secondary: str | None = None,
) -> dict[str, Any]:
    if comparator == "gte":
        status = "충족" if value >= threshold else "미달"
        rule = f">= {_format_percent(threshold)}"
    else:
        status = "충족" if value <= threshold else "미달"
        rule = f"<= {_format_percent(threshold)}"

    return {
        "label": label,
        "value": value,
        "value_display": _format_percent(value),
        "status": status,
        "rule": rule,
        "secondary": secondary,
    }


def _preview_value(value) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float):
        return f"{value:,.6f}".rstrip("0").rstrip(".")
    return str(value)


def _format_amount(value: float) -> str:
    return f"{value:,.4f}"


def _format_number(value: float) -> str:
    return f"{value:,.4f}".rstrip("0").rstrip(".")


def _format_percent(value: float) -> str:
    return f"{value * 100:,.2f}%"


def _format_date(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d")


def _format_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")
