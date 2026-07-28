"""Read-only access to data/curated (Parquet via DuckDB).

No financial math here — load and filter only.
"""

from smallcase_finance.data_access.exceptions import (
    CuratedDataUnavailable,
    SmallcaseNotFound,
)

__all__ = [
    "CuratedDataUnavailable",
    "SmallcaseNotFound",
]
