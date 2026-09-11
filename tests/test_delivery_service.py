from types import SimpleNamespace

from app.services import delivery_service


def zone(delivery_price: int, free_delivery_threshold: int | None):
    return SimpleNamespace(delivery_price=delivery_price, free_delivery_threshold=free_delivery_threshold)


def test_compute_fee_no_threshold_always_charges():
    z = zone(delivery_price=15000, free_delivery_threshold=None)
    assert delivery_service.compute_fee(z, items_subtotal=0) == 15000
    assert delivery_service.compute_fee(z, items_subtotal=1_000_000) == 15000


def test_compute_fee_below_threshold_charges_full_price():
    z = zone(delivery_price=15000, free_delivery_threshold=100_000)
    assert delivery_service.compute_fee(z, items_subtotal=99_999) == 15000


def test_compute_fee_at_threshold_is_free():
    z = zone(delivery_price=15000, free_delivery_threshold=100_000)
    assert delivery_service.compute_fee(z, items_subtotal=100_000) == 0


def test_compute_fee_above_threshold_is_free():
    z = zone(delivery_price=15000, free_delivery_threshold=100_000)
    assert delivery_service.compute_fee(z, items_subtotal=250_000) == 0
