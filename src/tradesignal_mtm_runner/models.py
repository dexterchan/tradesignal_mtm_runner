from __future__ import annotations
from pydantic import BaseModel, Field

import numpy as np
from enum import Enum
from datetime import datetime
from .exceptions import TradeNotYetClosedForPnlError, InvalidTradeStateError
import logging
from typing import Dict

logger = logging.getLogger(__name__)

MAX_NUMERIC_VALUE: float = 1e50
MIN_NUMERIC_VALUE: float = -1e50

class LongShort_Enum(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class Buy_Sell_Action_Enum(str, Enum):
    BUY = "B"
    SELL = "S"
    HOLD = "H"


class Proxy_Trade_Actions(str, Enum):
    SIGNAL = "SIGNAL"
    STOP_LOSS = "STOP_LOSS"
    ROI = "ROI"

class Inventory_Mode(str, Enum):
    LIFO = "L"
    FIFO = "F"
    WORST_PRICE = "W"

class Mtm_Result(BaseModel):
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


class ProxyTrade(BaseModel):
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
    inventory_mode:Inventory_Mode = Field(default=Inventory_Mode.WORST_PRICE)
    fee: float = Field(default=0.01)

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

    def calculate_mtm_normalized(self, price_diff: float) -> float:
        if price_diff is np.nan:
            return 0
        mtm = price_diff if self.direction == LongShort_Enum.LONG else -price_diff
        #return mtm
        return mtm / self.entry_price

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
            
        Args:
            other (ProxyTrade): [description]

        Raises:
            Exception: [description]

        Returns:
            [type]: [description]
        """
        if self.inventory_mode == Inventory_Mode.WORST_PRICE:
            # For Long direction, we pick the trade having largest entry price for closing or stop loss
            # For Short direction, we pick the trade having smallest entry price for closing or stop loss
            if self.direction != other.direction:
                raise Exception("Trade comparison failure... direction not matching")
            if self.direction == LongShort_Enum.LONG:
                return self.entry_price > other.entry_price
            else:
                return self.entry_price < other.entry_price
        elif self.inventory_mode == Inventory_Mode.FIFO:
            #First in first out
            return self.entry_datetime < self.entry_datetime
        elif self.inventory_mode == Inventory_Mode.LIFO:
            #Last in First out
            return self.entry_datetime > self.entry_datetime
