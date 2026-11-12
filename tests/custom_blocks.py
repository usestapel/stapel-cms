"""A project's own block type, registered fork-free in the registry tests."""
from pydantic import Field

from stapel_cms.blocks import BlockData


class PricingTable(BlockData):
    plans: list[str] = Field(min_length=1, max_length=5)


class NotAModel:
    pass
