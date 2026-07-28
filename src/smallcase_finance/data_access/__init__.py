"""Read-only access to data/curated (Parquet via DuckDB).

No financial math here — load and filter only.
"""

from smallcase_finance.data_access.exceptions import (
    CuratedDataUnavailable,
    SmallcaseNotFound,
)
from smallcase_finance.data_access.price_panel import (
    PricePanel,
    build_price_panel_from_rows,
    classify_data_source,
    load_price_panel,
)

__all__ = [
    "CuratedDataUnavailable",
    "SmallcaseNotFound",
    "PricePanel",
    "build_price_panel_from_rows",
    "classify_data_source",
    "load_price_panel",
]
