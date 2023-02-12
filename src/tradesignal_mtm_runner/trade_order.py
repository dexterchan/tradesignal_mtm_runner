from .exceptions import UnSupportedException, MaxPositionPerSymbolExceededException, NoShortPositionAllowedException
from datetime import datetime
from .models import  ProxyTrade, LongShort_Enum, Proxy_Trade_Actions
from .config import PnlCalcConfig
from typing import List
import heapq



#Copy from TradeOrderKeeper
# deprecated class to be replaced by TradeBookKeeperAgent
class TradeOrderSimulator:
    """Trade Order keeper keeps all outstanding trades and historical trades
    when Pnl Calculator run through the market data with the buy/sell signals
    It will contains two lists:
    - long trade position list
    - short trade position list
    When handling a buy signal, it will determine either:
    - open a new trade position in long list
    - close existing short trade position -> a pnl event will create
    - No action due to risk limit or no short position to close

    When handling a sell signal, it will determine either:
    - if short position enabled, open a new trade position in short list
    - close existing long trade positon -> a pnl event will create
    - no action due to risk limit or no long position to close
    """

    def __init__(
        self, symbol: str, pnl_config: PnlCalcConfig, fixed_unit: bool = True
    ) -> None:

        self.outstanding_long_position_list: List[ProxyTrade] = []
        self.outstanding_short_position_list: List[ProxyTrade] = []

        self.archive_long_positions_list: List[ProxyTrade] = []
        self.archive_short_positions_list: List[ProxyTrade] = []

        self.symbol = symbol
        self.enable_short_position = pnl_config.enable_short_position
        self.fixed_unit = fixed_unit
        self.max_position_per_symbol = pnl_config.max_position_per_symbol

        pass

    def get_highest_price_buy_position(self) -> ProxyTrade:
        """Get the highest price buy position for stop loss checking

        Returns:
            ProxyTrade: [description] or None if no trade
        """
        return (
            self.outstanding_long_position_list[0]
            if len(self.outstanding_long_position_list) > 0
            else None
        )

    def get_lowest_price_sell_position(self) -> ProxyTrade:
        """Get the lowest price sell position for stop loss checking

        Returns:
            ProxyTrade: [description] or None if no trade
        """
        return (
            self.outstanding_short_position_list[0]
            if len(self.outstanding_short_position_list) > 0
            else None
        )

    def _close_position(
        self,
        trade_pos: ProxyTrade,
        exit_price: float,
        time: datetime,
        close_reason: Proxy_Trade_Actions,
    ) -> tuple[ProxyTrade, ProxyTrade]:
        """Close the trade pos and generate a new trade with the exist price
            The trade_pos will be modified with closing
        Args:
            trade_pos (ProxyTrade): [description]
            exit_price (float): [description]
            time (datetime) : timestamp of the trade
        Raises:
            UnSupportedException: [description]

        Returns:
            ProxyTrade: [new trade, old trade] : old trade contains pnl
        """
        if not self.fixed_unit:
            raise UnSupportedException("Need to be fixed amount when closing position")
        new_trade: ProxyTrade = trade_pos.copy()
        new_dt = time
        trade_pos.close_position(
            exit_price=exit_price, exit_datetime=new_dt, close_reason=close_reason
        )

        new_trade.entry_datetime = new_dt
        new_trade.direction = (
            LongShort_Enum.SHORT
            if trade_pos.direction == LongShort_Enum.LONG
            else LongShort_Enum.LONG
        )
        new_trade.entry_price = exit_price
        return new_trade, trade_pos

    def _check_max_position_breach_per_symbol(self) -> bool:
        return (
            len(self.outstanding_long_position_list) >= self.max_position_per_symbol
            or len(self.outstanding_short_position_list) >= self.max_position_per_symbol
        )

    def handle_buy_signal(
        self,
        close_price: float,
        ts: datetime,
        unit: float,
        action_source: Proxy_Trade_Actions,
    ) -> tuple[ProxyTrade, ProxyTrade]:
        """handle buy signal

        Args:
            close_price (float): [description]
            ts (datetime): [description]
            unit (float) : buy unit
            action_source (Proxy_Trade_Actions) : Action Source to trigger buy signal

        Raises:
            MaxPositionPerSymbolExceededException: Position exceed the limit per symbol

        Returns:
            Tuple[ProxyTrade, ProxyTrade]: new trade , old trade (None if new position ; otherwise, a closed trade position)
        """

        new_trade: ProxyTrade = None
        old_trade: ProxyTrade = None
        short_pos: ProxyTrade = (
            heapq.heappop(self.outstanding_short_position_list)
            if self.enable_short_position
            and len(self.outstanding_short_position_list) > 0
            else None
        )
        if short_pos is not None:
            # It is a short position
            # close pos
            new_trade, old_trade = self._close_position(
                trade_pos=short_pos,
                exit_price=close_price,
                time=ts,
                close_reason=action_source,
            )
            self.archive_short_positions_list.append(short_pos)
        else:
            if self._check_max_position_breach_per_symbol():
                raise MaxPositionPerSymbolExceededException(
                    f"Current Long position breached:{len(self.outstanding_long_position_list)}"
                )
            # Create new pos
            new_trade = ProxyTrade(
                symbol=self.symbol,
                entry_datetime=ts,
                entry_price=close_price,
                unit=unit,
                direction=LongShort_Enum.LONG,
            )
            heapq.heappush(self.outstanding_long_position_list, new_trade)
        return new_trade, old_trade

    def handle_sell_signal(
        self,
        close_price: float,
        ts: datetime,
        unit: float,
        action_source: Proxy_Trade_Actions,
    ) -> ProxyTrade:
        """handle sell signal

        Args:
            close_price (float): [description]
            ts (datetime): [description]
            unit (float) : sell unit
            action_source (Proxy_Trade_Actions) : Action Source to trigger sell signal

        Raises:
            MaxPositionPerSymbolExceededException: Position exceed the limit per symbol

        Returns:
            ProxyTrade: [description]
        """
        new_trade: ProxyTrade = None
        old_trade: ProxyTrade = None
        if (
            not self.enable_short_position
            and len(self.outstanding_long_position_list) == 0
        ):
            raise NoShortPositionAllowedException()
        if len(self.outstanding_long_position_list) > 0:
            # It is a long position, now close it with a sell trade
            long_pos: ProxyTrade = heapq.heappop(self.outstanding_long_position_list)
            new_trade, old_trade = self._close_position(
                trade_pos=long_pos,
                exit_price=close_price,
                time=ts,
                close_reason=action_source,
            )
            self.archive_long_positions_list.append(long_pos)
        else:
            if self._check_max_position_breach_per_symbol():
                raise MaxPositionPerSymbolExceededException(
                    f"Current Short position breached:{len(self.outstanding_short_position_list)}"
                )
            new_trade = ProxyTrade(
                symbol=self.symbol,
                entry_datetime=ts,
                entry_price=close_price,
                direction=LongShort_Enum.SHORT,
                unit=unit,
            )
            heapq.heappush(self.outstanding_short_position_list, new_trade)

        return new_trade, old_trade

    @property
    def long_trades_archives(self) -> List[ProxyTrade]:
        return self.archive_long_positions_list

    @property
    def short_trades_archives(self) -> List[ProxyTrade]:
        return self.archive_short_positions_list

    @property
    def long_trades_outstanding(self) -> List[ProxyTrade]:
        return self.outstanding_long_position_list

    @property
    def short_trades_outstanding(self) -> List[ProxyTrade]:
        return self.outstanding_short_position_list

    def get_long_trades_archive(self, symbol: str) -> List[ProxyTrade]:
        """get Long trade archive (deprecated)

        Args:
            symbol (str): [description]

        Returns:
            List[ProxyTrade]: [description]
        """
        return self.archive_long_positions_list

    def get_short_trades_archive(self, symbol: str) -> List[ProxyTrade]:
        """get short trade archive (deprecated)

        Args:
            symbol (str): [description]

        Returns:
            List[ProxyTrade]: [description]
        """
        return self.archive_short_positions_list

    def get_long_trades_oustanding(self, symbol: str) -> List[ProxyTrade]:
        """get remain Long trade outstanding (deprecated)

        Args:
            symbol (str): [description]

        Returns:
            List[ProxyTrade]: [description]
        """
        return self.outstanding_long_position_list

    def get_short_trades_oustanding(self, symbol: str) -> List[ProxyTrade]:
        """get remain short trade outstanding (deprecated)

        Args:
            symbol (str): [description]

        Returns:
            List[ProxyTrade]: [description]
        """
        return self.outstanding_short_position_list
