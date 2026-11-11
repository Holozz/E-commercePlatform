from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .models import Candidate, Evidence, SampleRecord, SearchRun, WorkTask


class SearchUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class MarginResult:
    revenue: Decimal
    known_cost: Decimal
    contribution: Decimal | None
    margin_rate: Decimal | None
    missing_costs: list[str]
    passes_threshold: bool


def calculate_margin(
    revenue: Decimal,
    purchase: Decimal | None,
    shipping_packaging: Decimal | None,
    platform_fees: Decimal | None,
    ad_allocation: Decimal | None,
    after_sales_loss: Decimal | None,
) -> MarginResult:
    values = {
        "采购成本": purchase,
        "物流包装": shipping_packaging,
        "平台费用": platform_fees,
        "广告分摊": ad_allocation,
        "预计售后损失": after_sales_loss,
    }
    missing = [name for name, value in values.items() if value is None]
    known_cost = sum((value for value in values.values() if value is not None), Decimal("0"))
    if missing or revenue <= 0:
        return MarginResult(revenue, known_cost, None, None, missing, False)
    contribution = revenue - known_cost
    rate = contribution / revenue
    return MarginResult(
        revenue,
        known_cost,
        contribution,
        rate,
        [],
        contribution >= Decimal("5") and rate >= Decimal("0.20"),
    )


def record_sample(
    db: Session,
    candidate: Candidate,
    *,
    verdict: str,
    measured_size_mm: str | None = None,
    measured_sheet_count: int | None = None,
    packaging_result: str | None = None,
    writing_result: str | None = None,
    notes: str | None = None,
) -> SampleRecord:
    record = SampleRecord(
        candidate_id=candidate.id,
        verdict=verdict,
        measured_size_mm=measured_size_mm,
        measured_sheet_count=measured_sheet_count,
        packaging_result=packaging_result,
        writing_result=writing_result,
        notes=notes,
    )
    db.add(record)
    candidate.status = {
        "通过": "验样通过",
        "不通过": "验样未通过",
    }.get(verdict, "验样待复核")
    candidate.is_whitelisted = verdict == "通过"
    db.commit()
    return record


def run_brave_search(db: Session, query: str) -> SearchRun:
    used = db.scalar(select(func.count(SearchRun.id)).where(SearchRun.run_date == date.today())) or 0
    if used >= settings.daily_search_limit:
        raise SearchUnavailable(f"今日检索额度已用完（{settings.daily_search_limit} 次）")
    if not settings.brave_search_api_key:
        raise SearchUnavailable("未配置 BRAVE_SEARCH_API_KEY，真实搜索尚未连接")

    run = SearchRun(query=query, status="执行中")
    db.add(run)
    db.commit()
    try:
        response = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": 10, "country": "CN", "search_lang": "zh-hans"},
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": settings.brave_search_api_key,
                "Api-Version": "2023-01-01",
            },
            timeout=20,
        )
        response.raise_for_status()
        results = response.json().get("web", {}).get("results", [])
        created = 0
        for item in results:
            url = item.get("url")
            title = item.get("title")
            if not url or not title or db.scalar(select(Candidate.id).where(Candidate.source_url == url)):
                continue
            candidate = Candidate(title=title[:300], source_url=url, source_type="brave")
            candidate.evidences.append(
                Evidence(source_url=url, excerpt=(item.get("description") or "搜索结果未提供摘要")[:4000])
            )
            db.add(candidate)
            db.flush()
            db.add(
                WorkTask(
                    candidate_id=candidate.id,
                    task_type="补全商品事实",
                    reason="搜索仅提供标题与摘要，需要读取页面或人工补充规格、报价和代发条件。",
                )
            )
            created += 1
        run.status = "成功"
        run.result_count = created
        db.commit()
    except (httpx.HTTPError, ValueError) as exc:
        run.status = "失败"
        run.error = str(exc)[:1000]
        db.commit()
    return run

