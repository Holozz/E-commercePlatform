from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .config import settings
from .db import Base, engine, get_db
from .models import Candidate, Evidence, Quote, SampleRecord, Supplier, WorkTask
from .services import SearchUnavailable, calculate_margin, record_sample, run_brave_search

BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="纸迹工作台", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def redirect(path: str, message: str) -> RedirectResponse:
    return RedirectResponse(f"{path}?message={quote(message)}", status_code=303)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    stats = {
        "candidates": db.scalar(select(func.count(Candidate.id))) or 0,
        "pending": db.scalar(select(func.count(WorkTask.id)).where(WorkTask.status == "待处理")) or 0,
        "sampled": db.scalar(select(func.count(SampleRecord.id))) or 0,
        "whitelisted": db.scalar(select(func.count(Candidate.id)).where(Candidate.is_whitelisted)) or 0,
    }
    tasks = db.scalars(select(WorkTask).where(WorkTask.status == "待处理").order_by(WorkTask.id.desc()).limit(8)).all()
    recent = db.scalars(select(Candidate).order_by(Candidate.id.desc()).limit(6)).all()
    return templates.TemplateResponse(request, "dashboard.html", {"stats": stats, "tasks": tasks, "recent": recent, "settings": settings})


@app.get("/candidates", response_class=HTMLResponse)
def candidates(request: Request, db: Session = Depends(get_db)):
    items = db.scalars(select(Candidate).options(selectinload(Candidate.supplier)).order_by(Candidate.id.desc())).all()
    return templates.TemplateResponse(request, "candidates.html", {"items": items})


@app.post("/candidates")
def add_candidate(
    title: str = Form(...),
    source_url: str = Form(""),
    supplier_name: str = Form(""),
    excerpt: str = Form(""),
    db: Session = Depends(get_db),
):
    normalized_url = source_url.strip() or f"offline://manual/{uuid4()}"
    if db.scalar(select(Candidate.id).where(Candidate.source_url == normalized_url)):
        return redirect("/candidates", "这个来源链接已经存在")
    supplier = None
    if supplier_name.strip():
        supplier = db.scalar(select(Supplier).where(Supplier.name == supplier_name.strip()))
        if not supplier:
            supplier = Supplier(name=supplier_name.strip())
            db.add(supplier)
    item = Candidate(
        title=title.strip(),
        source_url=normalized_url,
        source_type="manual" if source_url.strip() else "offline",
        supplier=supplier,
    )
    item.evidences.append(Evidence(source_url=normalized_url, excerpt=excerpt.strip() or "人工录入，尚未附证据摘录"))
    db.add(item)
    db.flush()
    db.add(WorkTask(candidate_id=item.id, task_type="补全商品事实", reason="人工录入候选，需要补充规格、报价和代发条件。"))
    db.commit()
    return redirect(f"/candidates/{item.id}", "候选已保存")


@app.post("/search")
def search(query: str = Form(...), db: Session = Depends(get_db)):
    try:
        run = run_brave_search(db, query.strip())
    except SearchUnavailable as exc:
        return redirect("/candidates", str(exc))
    message = f"检索完成，新增 {run.result_count} 条候选" if run.status == "成功" else f"检索失败：{run.error}"
    return redirect("/candidates", message)


@app.get("/candidates/{candidate_id}", response_class=HTMLResponse)
def candidate_detail(candidate_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.scalar(
        select(Candidate)
        .where(Candidate.id == candidate_id)
        .options(selectinload(Candidate.supplier), selectinload(Candidate.evidences), selectinload(Candidate.quotes), selectinload(Candidate.samples))
    )
    return templates.TemplateResponse(request, "candidate_detail.html", {"item": item})


@app.post("/candidates/{candidate_id}/facts")
def update_facts(
    candidate_id: int,
    sku: str = Form(""), size_mm: str = Form(""), sheet_count: str = Form(""), page_count: str = Form(""),
    paper_gsm: str = Form(""), ruling: str = Form(""), binding: str = Form(""), cover_material: str = Form(""),
    pack_quantity: str = Form(""), weight_grams: str = Form(""), dropship_claimed: str = Form("unknown"),
    db: Session = Depends(get_db),
):
    item = db.get(Candidate, candidate_id)
    for field, value in {"sheet_count": sheet_count, "page_count": page_count, "paper_gsm": paper_gsm, "pack_quantity": pack_quantity, "weight_grams": weight_grams}.items():
        setattr(item, field, int(value) if value.strip() else None)
    for field, value in {"sku": sku, "size_mm": size_mm, "ruling": ruling, "binding": binding, "cover_material": cover_material}.items():
        setattr(item, field, value.strip() or None)
    item.dropship_claimed = {"yes": True, "no": False}.get(dropship_claimed)
    item.status = "待报价"
    db.commit()
    return redirect(f"/candidates/{candidate_id}", "商品事实已更新")


@app.post("/candidates/{candidate_id}/quotes")
def add_quote(
    candidate_id: int, sku: str = Form(...), quantity_from: int = Form(1), unit_cost: Decimal = Form(...),
    shipping_cost: str = Form(""), valid_until: str = Form(""), db: Session = Depends(get_db),
):
    db.add(Quote(candidate_id=candidate_id, sku=sku.strip(), quantity_from=quantity_from, unit_cost=unit_cost,
                 shipping_cost=Decimal(shipping_cost) if shipping_cost.strip() else None,
                 valid_until=date.fromisoformat(valid_until) if valid_until else None))
    item = db.get(Candidate, candidate_id)
    item.status = "待验样" if shipping_cost.strip() else "运费待确认"
    db.commit()
    return redirect(f"/candidates/{candidate_id}", "报价快照已保存")


@app.post("/candidates/{candidate_id}/samples")
def add_sample(
    candidate_id: int, verdict: str = Form(...), measured_size_mm: str = Form(""), measured_sheet_count: str = Form(""),
    packaging_result: str = Form(""), writing_result: str = Form(""), notes: str = Form(""), db: Session = Depends(get_db),
):
    item = db.get(Candidate, candidate_id)
    record_sample(
        db,
        item,
        verdict=verdict,
        measured_size_mm=measured_size_mm or None,
        measured_sheet_count=int(measured_sheet_count) if measured_sheet_count else None,
        packaging_result=packaging_result or None,
        writing_result=writing_result or None,
        notes=notes or None,
    )
    return redirect(f"/candidates/{candidate_id}", "验样结论已记录")


@app.post("/margin", response_class=HTMLResponse)
def margin(
    request: Request, revenue: Decimal = Form(...), purchase: str = Form(""), shipping_packaging: str = Form(""),
    platform_fees: str = Form(""), ad_allocation: str = Form(""), after_sales_loss: str = Form(""),
):
    def number(value: str) -> Decimal | None:
        try:
            return Decimal(value) if value.strip() else None
        except InvalidOperation:
            return None
    result = calculate_margin(revenue, number(purchase), number(shipping_packaging), number(platform_fees), number(ad_allocation), number(after_sales_loss))
    return templates.TemplateResponse(request, "margin.html", {"result": result})

