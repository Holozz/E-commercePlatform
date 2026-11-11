from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    contact_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    source_url: Mapped[str] = mapped_column(Text, unique=True)
    source_type: Mapped[str] = mapped_column(String(30), default="manual")
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    status: Mapped[str] = mapped_column(String(30), default="待补全")
    sku: Mapped[str | None] = mapped_column(String(120))
    size_mm: Mapped[str | None] = mapped_column(String(80))
    sheet_count: Mapped[int | None]
    page_count: Mapped[int | None]
    paper_gsm: Mapped[int | None]
    ruling: Mapped[str | None] = mapped_column(String(100))
    binding: Mapped[str | None] = mapped_column(String(100))
    cover_material: Mapped[str | None] = mapped_column(String(100))
    pack_quantity: Mapped[int | None]
    weight_grams: Mapped[int | None]
    dropship_claimed: Mapped[bool | None]
    is_whitelisted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    supplier: Mapped[Supplier | None] = relationship()
    evidences: Mapped[list["Evidence"]] = relationship(cascade="all, delete-orphan")
    quotes: Mapped[list["Quote"]] = relationship(cascade="all, delete-orphan")
    samples: Mapped[list["SampleRecord"]] = relationship(cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidences"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    source_url: Mapped[str] = mapped_column(Text)
    excerpt: Mapped[str] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    sku: Mapped[str] = mapped_column(String(120))
    quantity_from: Mapped[int] = mapped_column(default=1)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    shipping_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    valid_until: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SampleRecord(Base):
    __tablename__ = "sample_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    verdict: Mapped[str] = mapped_column(String(30))
    measured_size_mm: Mapped[str | None] = mapped_column(String(80))
    measured_sheet_count: Mapped[int | None]
    packaging_result: Mapped[str | None] = mapped_column(String(200))
    writing_result: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SearchRun(Base):
    __tablename__ = "search_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(String(600))
    status: Mapped[str] = mapped_column(String(30))
    result_count: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)
    run_date: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkTask(Base):
    __tablename__ = "work_tasks"
    __table_args__ = (UniqueConstraint("candidate_id", "task_type", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int | None] = mapped_column(ForeignKey("candidates.id"))
    task_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="待处理")
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

