"""
Sortino pairlist filter
"""
import logging
import sys
from datetime import timedelta
from typing import Any, Dict, List, Optional

import numpy as np
from cachetools import TTLCache
from pandas import DataFrame

from freqtrade.constants import Config, ListPairsWithTimeframes
from freqtrade.exceptions import OperationalException
from freqtrade.exchange.types import Tickers
from freqtrade.misc import plural
from freqtrade.plugins.pairlist.IPairList import IPairList, PairlistParameter
from freqtrade.util import dt_floor_day, dt_now, dt_ts


logger = logging.getLogger(__name__)


class SortinoFilter(IPairList):
    """
    Filters pairs by volatility
    """

    def __init__(self, exchange, pairlistmanager,
                 config: Config, pairlistconfig: Dict[str, Any],
                 pairlist_pos: int) -> None:
        super().__init__(exchange, pairlistmanager, config, pairlistconfig, pairlist_pos)

        self._days = pairlistconfig.get('lookback_days', 10)
        self._min_sortino_ratio = pairlistconfig.get('min_sortino_ratio', 0)
        self._refresh_period = pairlistconfig.get('refresh_period', 1440)
        self._def_candletype = self._config['candle_type_def']
        self._sort_direction: Optional[str] = pairlistconfig.get('sort_direction', None)

        self._pair_cache: TTLCache = TTLCache(maxsize=1000, ttl=self._refresh_period)

        candle_limit = exchange.ohlcv_candle_limit('1d', self._config['candle_type_def'])
        if self._days < 1:
            raise OperationalException("SortinoFilter requires lookback_days to be >= 1")
        if self._days > candle_limit:
            raise OperationalException("SortinoFilter requires lookback_days to not "
                                       f"exceed exchange max request size ({candle_limit})")
        if self._sort_direction not in [None, 'asc', 'desc']:
            raise OperationalException("SortinoFilter requires sort_direction to be "
                                       "either None (undefined), 'asc' or 'desc'")

    @property
    def needstickers(self) -> bool:
        """
        Boolean property defining if tickers are necessary.
        If no Pairlist requires tickers, an empty List is passed
        as tickers argument to filter_pairlist
        """
        return False

    def short_desc(self) -> str:
        """
        Short whitelist method description - used for startup-messages
        """
        return (f"{self.name} - Filtering pairs with "
                f"minimum sortino ratio {self._min_sortino_ratio} "
                f" the last {self._days} {plural(self._days, 'day')}.")

    @staticmethod
    def description() -> str:
        return "Filter pairs by their recent sortino ratio."

    @staticmethod
    def available_parameters() -> Dict[str, PairlistParameter]:
        return {
            "lookback_days": {
                "type": "number",
                "default": 10,
                "description": "Lookback Days",
                "help": "Number of days to look back at.",
            },
            "min_sortino_ratio": {
                "type": "number",
                "default": 0,
                "description": "Minimum Sortino",
                "help": "Minimum Sortino ratio a pair must have to be considered.",
            },
            "sort_direction": {
                "type": "option",
                "default": None,
                "options": ["", "asc", "desc"],
                "description": "Sort pairlist",
                "help": "Sort Pairlist ascending or descending by volatility.",
            },
            **IPairList.refresh_period_parameter()
        }

    def filter_pairlist(self, pairlist: List[str], tickers: Tickers) -> List[str]:
        """
        Validate trading range
        :param pairlist: pairlist to filter or sort
        :param tickers: Tickers (from exchange.get_tickers). May be cached.
        :return: new allowlist
        """
        needed_pairs: ListPairsWithTimeframes = [
            (p, '1d', self._def_candletype) for p in pairlist if p not in self._pair_cache]

        since_ms = dt_ts(dt_floor_day(dt_now()) - timedelta(days=self._days))
        candles = self._exchange.refresh_ohlcv_with_cache(needed_pairs, since_ms=since_ms)

        resulting_pairlist: List[str] = []
        sortino: Dict[str, float] = {}
        for p in pairlist:
            daily_candles = candles.get((p, '1d', self._def_candletype), None)

            sortino_ratio = self._calculate_sortino(p, daily_candles)

            if sortino_ratio is not None:
                if self._validate_pair_loc(p, sortino_ratio):
                    resulting_pairlist.append(p)
                    sortino[p] = (
                        sortino_ratio if sortino_ratio and not np.isnan(sortino_ratio) else 0
                    )
            else:
                self.log_once(f"Removed {p} from whitelist, no candles found.", logger.info)

        if self._sort_direction:
            resulting_pairlist = sorted(resulting_pairlist,
                                        key=lambda p: sortino[p],
                                        reverse=self._sort_direction == 'desc')
        return resulting_pairlist

    def _calculate_sortino(self, pair: str,  daily_candles: DataFrame) -> Optional[float]:
        if (sortino_ratio := self._pair_cache.get(pair, None)) is not None:
            return sortino_ratio

        if daily_candles is not None and not daily_candles.empty:
            returns = (daily_candles["close"].shift(1) / daily_candles["close"]) - 1
            returns.fillna(0, inplace=True)

            returns = returns.iloc[-self._days:]
            expected_returns_mean = returns.mean()
            total_downside = returns.loc[returns < 0]
            down_stdev = np.sqrt((total_downside**2).sum() / len(total_downside))

            if down_stdev != 0:
                sortino_ratio = expected_returns_mean / down_stdev * np.sqrt(self._days)
            else:
                # Define high (negative) sortino ratio to be clear that this is NOT optimal.
                sortino_ratio = -20.0
            return sortino_ratio
        else:
            return None

    def _validate_pair_loc(self, pair: str, sortino_ratio: float) -> bool:
        """
        Validate trading range
        :param pair: Pair that's currently validated
        :param sortino_ratio: Sortino Ratio
        :return: True if the pair can stay, false if it should be removed
        """

        if self._min_sortino_ratio >= sortino_ratio:
            result = True
        else:
            self.log_once(f"Removed {pair} from whitelist, because sortino ratio "
                          f"under {self._days} {plural(self._days, 'day')} "
                          f"is: {sortino_ratio:.3f} "
                          f"which is not in the configured minimum ratio "
                          f"{self._min_sortino_ratio}.",
                          logger.info)
            result = False
        return result
