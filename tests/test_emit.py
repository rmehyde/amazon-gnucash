import pytest

from finances.emit import shorten


@pytest.mark.parametrize(
    "name, short",
    [
        ("Magnetic Hooks, 4 Pack", "Magnetic Hooks"),
        ("Shaving Cream - Sensitive Skin, 7 oz", "Shaving Cream"),
        ("Desk Lamp – Dimmable", "Desk Lamp"),  # en dash
        ("Brightside Micellar Water with Salicylic Acid", "Brightside Micellar Water"),
        ("Case WITH Strap", "Case"),
        ("Wireless Earbuds | Bluetooth 5.3", "Wireless Earbuds"),
        ("Q-Tips Swabs, Size 375", "Q-Tips Swabs"),  # a dash inside a word stays
        ("Sink Strainer Basket", "Sink Strainer Basket"),
        ("Wool Socks without Seams", "Wool Socks without Seams"),  # not "with"
        ("With Love, a Novel", "With Love"),  # cutting at "With" would leave nothing
    ],
)
def test_shortens_names_to_the_product(name, short):
    assert shorten(name) == short
