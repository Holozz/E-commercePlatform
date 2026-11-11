import pytest

from app.models import Candidate
from app.services import (
    ExtractedFact,
    PageReadError,
    ProductExtraction,
    _validate_public_url,
    apply_extraction,
    html_to_text,
)


def test_html_text_excludes_scripts_and_limits_length():
    content = "<html><style>hidden</style><body><h1>A5 横线本</h1><script>ignore()</script><p>80 张</p></body></html>"
    assert html_to_text(content) == "A5 横线本\n80 张"


def test_page_reader_rejects_private_addresses():
    with pytest.raises(PageReadError, match="内网"):
        _validate_public_url("http://127.0.0.1/private")


def test_ai_extraction_updates_supported_facts_and_revokes_whitelist():
    candidate = Candidate(
        title="A5 本",
        source_url="https://example.com/a5",
        status="验样通过",
        is_whitelisted=True,
    )
    extraction = ProductExtraction(
        facts=[
            ExtractedFact(field="size_mm", value="148 × 210", evidence_text="规格：148×210mm"),
            ExtractedFact(field="sheet_count", value="80", evidence_text="内页80张"),
            ExtractedFact(field="page_count", value="160", evidence_text=None),
            ExtractedFact(field="unknown", value="x", evidence_text="x"),
        ],
        missing_fields=["paper_gsm"],
        conflicts=[],
    )

    changed = apply_extraction(candidate, extraction)

    assert changed == ["size_mm", "sheet_count"]
    assert candidate.size_mm == "148 × 210"
    assert candidate.sheet_count == 80
    assert candidate.page_count is None
    assert candidate.is_whitelisted is False
    assert candidate.status == "AI 提取待复核"


def test_ai_extraction_does_not_overwrite_existing_conflicting_fact():
    candidate = Candidate(
        title="人工核验本",
        source_url="https://example.com/checked",
        sheet_count=80,
        status="验样通过",
        is_whitelisted=True,
    )
    extraction = ProductExtraction(
        facts=[ExtractedFact(field="sheet_count", value="60", evidence_text="页面写60张")],
        missing_fields=[],
        conflicts=[],
    )

    changed = apply_extraction(candidate, extraction)

    assert changed == []
    assert candidate.sheet_count == 80
    assert candidate.is_whitelisted is False
    assert candidate.status == "AI 提取待复核"

