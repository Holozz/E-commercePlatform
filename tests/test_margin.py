from decimal import Decimal

from app.services import calculate_margin


def test_missing_cost_is_not_treated_as_zero():
    result = calculate_margin(
        revenue=Decimal("30"), purchase=Decimal("10"), shipping_packaging=None,
        platform_fees=Decimal("1"), ad_allocation=Decimal("0"), after_sales_loss=Decimal("1"),
    )
    assert result.contribution is None
    assert result.missing_costs == ["物流包装"]
    assert result.passes_threshold is False


def test_margin_threshold_requires_amount_and_rate():
    result = calculate_margin(
        revenue=Decimal("30"), purchase=Decimal("15"), shipping_packaging=Decimal("3"),
        platform_fees=Decimal("1"), ad_allocation=Decimal("0"), after_sales_loss=Decimal("1"),
    )
    assert result.contribution == Decimal("10")
    assert result.margin_rate == Decimal("10") / Decimal("30")
    assert result.passes_threshold is True

