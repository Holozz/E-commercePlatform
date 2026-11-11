from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import Candidate
from app.services import record_sample


def test_only_passed_sample_enters_whitelist():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        candidate = Candidate(title="A5 横线本", source_url="https://example.com/a5")
        db.add(candidate)
        db.commit()

        record_sample(db, candidate, verdict="通过", measured_sheet_count=80)

        db.refresh(candidate)
        assert candidate.status == "验样通过"
        assert candidate.is_whitelisted is True
        assert candidate.samples[0].measured_sheet_count == 80


def test_failed_sample_removes_whitelist():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        candidate = Candidate(
            title="B5 记录本",
            source_url="https://example.com/b5",
            status="验样通过",
            is_whitelisted=True,
        )
        db.add(candidate)
        db.commit()

        record_sample(db, candidate, verdict="不通过", notes="实测张数不符")

        db.refresh(candidate)
        assert candidate.status == "验样未通过"
        assert candidate.is_whitelisted is False

