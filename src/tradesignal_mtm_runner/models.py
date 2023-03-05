from __future__ import annotations
from typing import  Dict

from pydantic import BaseModel, Field

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
    fee_rate: float = Field(default=0.01)

    @property
    def check_closed(self) -> bool:
        return self.is_closed

    def calculate_pnl(self, price: float, fee_included:bool=False) -> float:
        """calculate pnl based on the price

        Args:
            price (float): [description]

        Returns:
            float: [description]
        """
        pnl_value: float = price - self.entry_price if self.direction == LongShort_Enum.LONG else self.entry_price - price
        
        if fee_included:
            #adjusted by fee when entered
            pnl_value -= self.fee_rate * self.entry_price
            #adjusted by fee when closed
            if self.is_closed:
                pnl_value -= self.fee_rate * self.exit_price
        
        return pnl_value

    def calculate_pnl_normalized(self, price: float, fee_included:bool=False) -> float:
        return self.calculate_pnl(price=price, fee_included=fee_included) / self.entry_price

    def calculate_mtm_normalized(self, price_diff: float) -> float:
        """ calculate mtm from the price difference p(t) - p(t-1)

        Args:
            price_diff (float): price diff between p(t) and p(t-1)

        Returns:
            float: delta mtm
        """
        if price_diff is np.nan:
            return 0
        mtm = price_diff if self.direction == LongShort_Enum.LONG else -price_diff
        #return mtm
        return mtm / self.entry_price
    
    @property
    def fee_normalized(self) -> float:
        """ calculate normalized fee

        Returns:
            float: fee adjusted
        """
        return self.fee_rate 

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
        return self.calculate_pnl(price=self.exit_price, fee_included=True)

    @property
    def pnl_normalized(self) -> float:
        return self.calculate_pnl_normalized(price=self.exit_price, fee_included=True)

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
            #return self.entry_datetime > self.entry_datetime
            return self.entry_datetime < self.entry_datetime
        elif self.inventory_mode == Inventory_Mode.LIFO:
            #Last in First out
            #return self.entry_datetime < self.entry_datetime
            return self.entry_datetime > self.entry_datetime

    # def __gt__(self, other: ProxyTrade):
    #     """Comparator to sort the order of trade by entry price
            
    #     Args:
    #         other (ProxyTrade): [description]

    #     Raises:
    #         Exception: [description]

    #     Returns:
    #         [type]: [description]
    #     """
    #     return not self.__lt__(other=other)


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
    long_trades_archive: list[ProxyTrade] = Field(default_factory=list)
    short_trades_archive: list[ProxyTrade] = Field(default_factory=list)
    long_trades_outstanding: list[ProxyTrade] = Field(default_factory=list)
    short_trades_oustanding: list[ProxyTrade] = Field(default_factory=list)
    calc_log_folder: str = None

    def to_Dict(self) -> Dict:
        pdict: Dict = self.dict()
        pdict["long_trades_archive_size"] = len(self.long_trades_archive)
        pdict["short_trades_archive_size"] = len(self.short_trades_archive)
        pdict["long_trades_outstanding_size"] = len(self.long_trades_outstanding)
        pdict["short_trades_outstanding_size"] = len(self.short_trades_oustanding)
        return pdict

    def to_query_dict(self) -> Dict:
        fields_queryable = [
            "batch_id",
            "data_key",
            "strategy_name",
            "strategy_id",
            "pnl",
            "max_drawdown",
            "sharpe_ratio",
            "mkt_start_epoch",
            "mkt_end_epoch",
            "run_start_epoch",
            "run_end_epoch",
            "long_trades_archive_size",
            "short_trades_archive_size",
            "long_trades_outstanding_size",
            "short_trades_outstanding_size",
        ]
        _d = self.to_Dict()
        return {k: _d[k] for k in fields_queryable}

    def to_json_str(self) -> str:
        from datetime import datetime
        import json

        def _json_serial(obj):
            """JSON serializer for objects not serializable by default json code"""
            if isinstance(obj, (datetime)):
                return obj.isoformat()

        pdict: Dict = self.to_Dict()
        return json.dumps(pdict, default=_json_serial)

    def __repr__(self) -> str:
        return "Id:{}, pnl: {:.4f}, sharpe_ratio: {:.4f}, max_drawdown:{:.4f}, Parameters{}".format(
            self.strategy_id,
            self.pnl,
            self.sharpe_ratio,
            self.max_drawdown,
            self.params,
        )


