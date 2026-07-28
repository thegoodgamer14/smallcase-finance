"""Raw → curated data pipeline.

Run::

    python -m smallcase_finance.pipeline
    make data
"""

from smallcase_finance.pipeline.run import run_pipeline

__all__ = ["run_pipeline"]
