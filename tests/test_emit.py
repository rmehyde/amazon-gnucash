import pytest

from finances.emit import shorten


@pytest.mark.parametrize(
    "name, short",
    [
        (
            "Acme, Precise Refillable & Retractable Rolling Ball Pens, Extra Fine Point",
            "Acme, Precise Refillable & Retractable Rolling Ball Pens",
        ),
        (
            "Stainless Steel Pour Over Kettle for Coffee and Tea - 1.2 Liter",
            "Stainless Steel Pour Over Kettle for Coffee and Tea",
        ),
        (
            "Brightside Micellar Cleansing Water for All Skin Types with Salicylic Acid",
            "Brightside Micellar Cleansing Water for All Skin Types",
        ),
        (
            "Wireless Noise Cancelling Over-Ear Headphones | Bluetooth 5.3",
            "Wireless Noise Cancelling Over-Ear Headphones",
        ),
        # Dashes inside words, and "without", aren't cuts.
        (
            "Ceramic Non-Stick Frying Pan Set of Three Pieces, Oven-Safe",
            "Ceramic Non-Stick Frying Pan Set of Three Pieces",
        ),
        (
            "Merino Wool Hiking Socks for Men and Women without Seams",
            "Merino Wool Hiking Socks for Men and Women without Seams",
        ),
        # Names this short are already the product.
        ("Magnetic Hooks, 4 Pack", "Magnetic Hooks, 4 Pack"),
        ("Hero with a Thousand Faces", "Hero with a Thousand Faces"),
    ],
)
def test_shortens_long_names_to_the_product(name, short):
    assert shorten(name) == short
