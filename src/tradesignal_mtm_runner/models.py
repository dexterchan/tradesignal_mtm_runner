from __future__ import annotations
from dataclasses import dataclass, Field
from pydantic import BaseModel, validator
import numpy as np
from enum import Enum
from datetime import datetime
from .exceptions import TradeNotYetClosedForPnlError, InvalidTradeStateError
import logging

logger = logging.getLogger(__name__)

MAX_NUMERIC_VALUE: float = 1e50
MIN_NUMERIC_VALUE: float = -1e50

class LongShort_Enum(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class Proxy_Trade_Actions(str, Enum):
    SIGNAL = "SIGNAL"
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"


class PnlCalcConfig(BaseModel):
    """_summary_
        roi - Return On Investment (ROI):
        e.g. roi = {
            40: 0.0,
            30: 0.01,
            20: 0.02,
            0: 0.04
        }
        - Sell whenever 4% profit was reached
        - Sell when 2% profit was reached (in effect after 20 minutes)
        - Sell when 1% profit was reached (in effect after 30 minutes)
        - Sell when trade is non-loosing (in effect after 40 minutes)

        stoploss - profit ratio to stop loss
        fixed_stake_unit_amount - notional of each trade
        enable_short_position - enable short position
        max_position_per_symbol - number of open position per symbol

    Args:
        BaseModel (_type_): _description_

    Returns:
        _type_: _description_
    """

    roi: dict[int, float] = Field(default_factory=dict)
    stoploss: float = float("-inf")
    fixed_stake_unit_amount: float = 100
    enable_short_position: bool = False
    max_position_per_symbol: int = 1

    @classmethod
    def get_default(cls) -> PnlCalcConfig:
        return cls(roi={"0": float("inf")}, stoploss=float("-inf"))

    @validator("max_position_per_symbol")
    def max_position_per_symbol_validation(cls, v):
        assert isinstance(v, int)
        assert v > 0
        return v

    @validator("fixed_stake_unit_amount")
    def fixed_stake_unit_amount_validation(cls, v):
        assert isinstance(v, float)
        assert v > 0, "fixed unit amount should be > 0"
        return v

    @validator("stoploss")
    def stopless_validation(cls, v):
        assert v < 0, "must be less than 0 or greater than -1"
        return v

    @validator("roi")
    def roi_validation(cls, d):
        assert isinstance(d, dict), "roi should be Dict"
        assert len(d) > 0
        new_values = {}
        for k, v in d.items():
            assert isinstance(int(k), int), "roi key should be convertable to int"
            assert isinstance(v, float)
            assert int(k) >= 0, "roi key should be positive or zero"
            assert v >= 0, "roi value should be larger than 0"
            new_values[int(k)] = v
        assert 0 in new_values, "missing default roi"
        return new_values

@dataclass
class Mtm_Result:
    """ Class containing Mtm Result
    """
    strategy_id: str = None
    batch_id: str = None
    data_key: str = None
    strategy_name: str = None

    pnl: float = np.nan
    max_drawdown: float = np.nan
    sharpe_ratio: float = Field(default=np.nan)

    mkt_start_epoch: int = 0
    mkt_end_epoch: int = 0
    run_start_epoch: int = 0
    run_end_epoch: int = 0

    params: dict = Field(default_factory=dict)  # Strategy parameters
    pnl_timeline: dict = Field(default_factory=dict)  # Dict column form of pandas frame
    pnl_daily: dict = Field(default_factory=dict)  # Dict column form of pandas frame
    long_trades_archive: list[ProxyTrade] = Field(default_factory=list)
    short_trades_archive: list[ProxyTrade] = Field(default_factory=list)
    long_trades_outstanding: list[ProxyTrade] = Field(default_factory=list)
    short_trades_oustanding: list[ProxyTrade] = Field(default_factory=list)
    calc_log_folder: str = None

@dataclass
class ProxyTrade:
    symbol: str
    entry_price: float
    unit: float
    direction: LongShort_Enum
    entry_datetime: datetime
    exit_price: float = Field(default=-float("inf"))
    exit_datetime: datetime = Field(default=None)
    is_closed: bool = Field(default=False)
    close_reason: Proxy_Trade_Actions = Field(default=None)
    mtm_history: list[float] = Field(default_factory=list)

    @property
    def check_closed(self) -> bool:
        return self.is_closed

    def calculate_pnl(self, price: float) -> float:
        """calculate pnl based on the price

        Args:
            price (float): [description]

        Returns:
            float: [description]
        """
        if self.direction == LongShort_Enum.LONG:
            return price - self.entry_price
        else:
            return self.entry_price - price

    def calculate_pnl_normalized(self, price: float) -> float:
        return self.calculate_pnl(price=price) / self.entry_price

    @property
    def pnl(self) -> float:
        """calculate pnl for a closed trade

        Raises:
            TradeNotYetClosedForPnlError: [description]

        Returns:
            float: [description]
        """
        # logger.debug(f"Trade calcualte pnl - {self.is_closed}")
        if not self.is_closed:
            logger.error("Trade not yet closed")
            raise TradeNotYetClosedForPnlError("Trade is not yet closed... Invalid PNL")
        return self.calculate_pnl(price=self.exit_price)

    @property
    def pnl_normalized(self) -> float:
        return self.pnl / self.entry_price

    def close_position(
        self, exit_price: float, exit_datetime: datetime, close_reason: Proxy_Trade_Actions
    ) -> None:
        """Operate the closing position process

        Args:
            exit_price (float): [description]
            exit_datetime (datetime): [description]
            close_reason(close_reason) : Closing reason
        """
        if self.is_closed == True:
            raise InvalidTradeStateError(f"Trade is already closed: {self.is_closed}")
        self.exit_price = exit_price
        self.exit_datetime = exit_datetime
        self.is_closed = True
        self.close_reason = close_reason
        pass

    def __lt__(self, other: ProxyTrade):
        """Comparator to sort the order of trade by entry price
            For Long direction, we pick the trade having largest entry price for closing or stop loss
            For Short direction, we pick the trade having smallest entry price for closing or stop loss

        Args:
            other (ProxyTrade): [description]

        Raises:
            Exception: [description]

        Returns:
            [type]: [description]
        """
        if self.direction != other.direction:
            raise Exception("Trade comparison failure... direction not matching")
        if self.direction == LongShort_Enum.LONG:
            return self.entry_price > other.entry_price
        else:
            return self.entry_price < other.entry_price
