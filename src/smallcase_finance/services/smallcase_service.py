"""Smallcase list, detail, and holdings orchestration."""

from __future__ import annotations

from datetime import date
from typing import Optional

from smallcase_finance.data_access import SmallcaseNotFound
from smallcase_finance.data_access import smallcases as sc_da
from smallcase_finance.schemas.holdings import HoldingItem, HoldingsResponse
from smallcase_finance.schemas.smallcase import (
    SmallcaseDetail,
    SmallcaseListItem,
    SmallcaseListResponse,
)


class SmallcaseService:
    def list_smallcases(
        self,
        *,
        tag: Optional[str] = None,
        q: Optional[str] = None,
    ) -> SmallcaseListResponse:
        rows = sc_da.list_smallcases(tag=tag, q=q)
        items: list[SmallcaseListItem] = []
        for row in rows:
            sid = row["smallcase_id"]
            as_of = sc_da.latest_nav_as_of(sid)
            try:
                count = sc_da.constituent_count(sid, as_of=as_of)
            except Exception:
                count = None
            items.append(
                SmallcaseListItem(
                    id=sid,
                    name=row["name"],
                    description=row.get("description"),
                    theme=row.get("theme"),
                    currency=row.get("currency") or "INR",
                    methodology=row.get("methodology") or "custom_weights",
                    rebalance_rule=row.get("rebalance_rule") or "manual",
                    inception_date=row.get("inception_date"),
                    as_of=as_of,
                    constituent_count=count,
                )
            )
        return SmallcaseListResponse(items=items)

    def get_smallcase(self, smallcase_id: str) -> SmallcaseDetail:
        row = sc_da.get_smallcase(smallcase_id)
        return SmallcaseDetail(
            id=row["smallcase_id"],
            name=row["name"],
            description=row.get("description"),
            theme=row.get("theme"),
            currency=row.get("currency") or "INR",
            methodology=row.get("methodology") or "custom_weights",
            rebalance_rule=row.get("rebalance_rule") or "manual",
            base_nav=float(row.get("base_nav") or 100.0),
            inception_date=row.get("inception_date"),
            benchmark_id=row.get("benchmark_id"),
            notes=row.get("notes"),
        )

    def get_holdings(
        self,
        smallcase_id: str,
        *,
        as_of: Optional[date] = None,
    ) -> HoldingsResponse:
        # Ensure smallcase exists
        sc = sc_da.get_smallcase(smallcase_id)
        sid = sc["smallcase_id"]

        resolved_as_of = as_of
        if resolved_as_of is None:
            resolved_as_of = sc_da.latest_nav_as_of(sid) or sc.get("inception_date")
            if resolved_as_of is None:
                # still need a date for response; use today-less fallback via constituents
                constituents = sc_da.get_constituents(sid, as_of=None)
                if not constituents:
                    raise SmallcaseNotFound(sid)  # exists but no composition
                resolved_as_of = max(
                    c["effective_from"] for c in constituents if c.get("effective_from")
                )
            else:
                constituents = sc_da.get_constituents(sid, as_of=resolved_as_of)
        else:
            constituents = sc_da.get_constituents(sid, as_of=resolved_as_of)

        symbols = [c["symbol"] for c in constituents]
        instruments = sc_da.get_instruments(symbols) if symbols else {}

        holdings: list[HoldingItem] = []
        for c in constituents:
            inst = instruments.get(c["symbol"], {})
            holdings.append(
                HoldingItem(
                    symbol=c["symbol"],
                    name=inst.get("name"),
                    weight=float(c["target_weight"]),
                    sector=inst.get("sector"),
                )
            )
        holdings.sort(key=lambda h: h.symbol)

        weight_sum = sum(h.weight for h in holdings)
        effective_from = None
        if constituents:
            effective_from = constituents[0].get("effective_from")

        return HoldingsResponse(
            smallcase_id=sid,
            as_of=resolved_as_of,  # type: ignore[arg-type]
            effective_from=effective_from,
            methodology=sc.get("methodology"),
            holdings=holdings,
            weight_sum=round(weight_sum, 6),
        )
