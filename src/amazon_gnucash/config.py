import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator


class Config(BaseModel):
    """Where Amazon's payment methods land in GnuCash."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    accounts: dict[str, str]  # payment method as Amazon shows it -> GnuCash account
    skip: frozenset[str] = frozenset()  # payment methods to leave out entirely
    skip_merchants: frozenset[str] = frozenset()  # merchants to leave out, by name start
    uncategorized: str  # the GnuCash account items go to until categorized
    payers: dict[str, str] = {}  # Amazon login -> who paid, as written in Notes

    @model_validator(mode="after")
    def _skip_only_unmapped(self) -> "Config":
        if both := self.skip & self.accounts.keys():
            raise ValueError(f"cards both mapped and skipped: {sorted(both)}")
        return self


def load_config(path: Path) -> Config:
    with path.open("rb") as file:
        return Config.model_validate(tomllib.load(file))
