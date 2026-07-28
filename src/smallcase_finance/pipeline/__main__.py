"""Allow ``python -m smallcase_finance.pipeline``."""

from smallcase_finance.pipeline.run import main

if __name__ == "__main__":
    raise SystemExit(main())
