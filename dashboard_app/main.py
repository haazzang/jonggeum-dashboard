from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dashboard_app.calculations import build_dashboard
from dashboard_app.data_loader import load_raw_dataset
from dashboard_app.manual_metrics import ManualMetrics, load_manual_metrics, save_manual_metrics
from dashboard_app.settings import INPUT_DIR, ROOT_DIR


app = FastAPI(title="종금 대시보드")
app.mount("/static", StaticFiles(directory=ROOT_DIR / "dashboard_app" / "static"), name="static")
templates = Jinja2Templates(directory=str(ROOT_DIR / "dashboard_app" / "templates"))


@app.get("/")
def dashboard_page(request: Request):
    raw_dataset = load_raw_dataset()
    manual_metrics = load_manual_metrics(raw_dataset.dashboard_seed_metrics)
    dashboard = build_dashboard(raw_dataset, manual_metrics)
    return templates.TemplateResponse(
        name="index.html",
        request=request,
        context={"dashboard": dashboard},
    )


@app.get("/api/dashboard")
def dashboard_api():
    raw_dataset = load_raw_dataset()
    manual_metrics = load_manual_metrics(raw_dataset.dashboard_seed_metrics)
    dashboard = build_dashboard(raw_dataset, manual_metrics)
    return JSONResponse(content=dashboard)


@app.post("/upload")
async def upload_source(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="업로드된 파일이 없습니다.")

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if len(files) == 1 and Path(files[0].filename or "").suffix.lower() in {".xlsx", ".xlsm"}:
        target_path = INPUT_DIR / f"workbook_{timestamp}.xlsx"
        with target_path.open("wb") as output:
            shutil.copyfileobj(files[0].file, output)
        return RedirectResponse(url="/", status_code=303)

    target_dir = INPUT_DIR / f"csv_bundle_{timestamp}"
    target_dir.mkdir(parents=True, exist_ok=True)

    saved = {"deposits": None, "assets": None}
    for file in files:
        filename = file.filename or ""
        suffix = Path(filename).suffix.lower()
        if suffix != ".csv":
            continue
        if "수신잔고" in filename or "deposit" in filename.lower():
            target_path = target_dir / "deposits.csv"
            saved["deposits"] = target_path
        elif "운용자산" in filename or "asset" in filename.lower():
            target_path = target_dir / "assets.csv"
            saved["assets"] = target_path
        else:
            continue
        with target_path.open("wb") as output:
            shutil.copyfileobj(file.file, output)

    if not all(saved.values()):
        raise HTTPException(
            status_code=400,
            detail="CSV 업로드는 수신잔고/운용자산 파일 한 쌍이 필요합니다.",
        )

    return RedirectResponse(url="/", status_code=303)


@app.post("/manual-metrics")
def update_manual_metrics(
    venture_capital_issued_note_ratio: float = Form(...),
    venture_capital_company_wide_quarter_ratio: float = Form(...),
    liquidity_ratio_1m: float = Form(...),
    liquidity_ratio_3m: float = Form(...),
):
    metrics = ManualMetrics(
        venture_capital_issued_note_ratio=venture_capital_issued_note_ratio / 100.0,
        venture_capital_company_wide_quarter_ratio=venture_capital_company_wide_quarter_ratio / 100.0,
        liquidity_ratio_1m=liquidity_ratio_1m / 100.0,
        liquidity_ratio_3m=liquidity_ratio_3m / 100.0,
    )
    save_manual_metrics(metrics)
    return RedirectResponse(url="/", status_code=303)


@app.get("/health")
def healthcheck():
    return {"status": "ok"}
