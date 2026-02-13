"""Bloomberg data access wrapper with xbbg primary and blpapi fallback."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class BloombergConfig:
    """Configuration for Bloomberg session and defaults."""

    timeout: int = 5000
    use_xbbg: bool = True


class BloombergInterface:
    """Production-oriented Bloomberg wrapper supporting BDH/BDP/BDS/ECO.

    Methods are normalized to return pandas objects with consistent indexing.
    """

    def __init__(self, config: Optional[BloombergConfig] = None) -> None:
        self.config = config or BloombergConfig()
        self._xbbg = None
        self._blpapi = None
        self._connect()

    def _connect(self) -> None:
        """Initialize adapters lazily and log available backend."""
        if self.config.use_xbbg:
            try:
                from xbbg import blp  # type: ignore

                self._xbbg = blp
                logger.info("Connected using xbbg backend")
                return
            except Exception as exc:  # pragma: no cover - environment-dependent
                logger.warning("xbbg unavailable, falling back to blpapi: %s", exc)

        try:
            import blpapi  # type: ignore

            self._blpapi = blpapi
            logger.info("Initialized blpapi backend")
        except Exception as exc:
            raise RuntimeError("Neither xbbg nor blpapi backends are available") from exc

    def bdh(
        self,
        tickers: Sequence[str],
        flds: Sequence[str],
        start_date: str,
        end_date: str,
        overrides: Optional[dict] = None,
    ) -> pd.DataFrame:
        """Historical data request (BDH)."""
        if self._xbbg is None:
            raise NotImplementedError("BDH via blpapi fallback not yet implemented.")
        df = self._xbbg.bdh(
            tickers=list(tickers),
            flds=list(flds),
            start_date=start_date,
            end_date=end_date,
            **(overrides or {}),
        )
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ["|".join([str(c) for c in col]).strip("|") for col in df.columns]
        return df.sort_index()

    def bdp(self, tickers: Sequence[str], flds: Sequence[str], overrides: Optional[dict] = None) -> pd.DataFrame:
        """Reference data request (BDP)."""
        if self._xbbg is None:
            raise NotImplementedError("BDP via blpapi fallback not yet implemented.")
        return self._xbbg.bdp(tickers=list(tickers), flds=list(flds), **(overrides or {}))

    def bds(self, ticker: str, field: str, overrides: Optional[dict] = None) -> pd.DataFrame:
        """Bulk dataset request (BDS), e.g., index memberships."""
        if self._xbbg is None:
            raise NotImplementedError("BDS via blpapi fallback not yet implemented.")
        return self._xbbg.bds(ticker=ticker, flds=field, **(overrides or {}))

    def eco(self, tickers: Sequence[str], fields: Sequence[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Economic data pull convenience wrapper."""
        return self.bdh(tickers=tickers, flds=fields, start_date=start_date, end_date=end_date)

    def yield_curve(self, curve_tickers: Iterable[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Retrieve yield curve nodes or benchmark tenors."""
        return self.bdh(tickers=list(curve_tickers), flds=["PX_LAST"], start_date=start_date, end_date=end_date)

    def fx_spot_forward(self, spot_ticker: str, fwd_ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch spot and forward curves for FX carry and hedging analytics."""
        return self.bdh([spot_ticker, fwd_ticker], ["PX_LAST"], start_date=start_date, end_date=end_date)
