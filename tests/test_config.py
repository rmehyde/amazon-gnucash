from pathlib import Path

import pytest
from pydantic import ValidationError

from amazon_gnucash.config import load_config

FIXTURE = Path(__file__).parent / "fixtures" / "amazon.toml"


def test_rejects_card_both_mapped_and_skipped(tmp_path):
    config = tmp_path / "amazon.toml"
    config.write_text(FIXTURE.read_text().replace("Mastercard ****5555", "Visa ****4242"))

    with pytest.raises(ValidationError, match=r"Visa \*\*\*\*4242"):
        load_config(config)
