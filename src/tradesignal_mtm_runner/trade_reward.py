from __future__ import annotations
from .config import PnlCalcConfig
from .models import ProxyTrade, Buy_Sell_Action_Enum, Proxy_Trade_Actions
from .helper import ROI_Helper
from datetime import datetime
from .utility import convert_datetime_to_ms
import logging
import numpy as np


logger = logging.getLogger(__name__)
class TradeBookKeeperAgent:
    """ The Book Keeper keeps all outstanding trades and archive historical trades
        It will contains two lists:
        - long trade position list
        - short trade position list

        Given a timestamp - t , price - p(t), trade signal - s(t), it works out
        - instant mtm(t) at timestamp t with p(t) with all outstanding trades
        - For each outstanding trade, run through ROI at t with p(t) to see if we close the trade
        - For each outstanding trade, run through stop/loss at t with p(t) to see of we close the trade
        - handle buy/sell position at t with p(t) and s(t)

        at any time t, we would work out Sharpe ratio with mtm(t)
    """

    def __init__(
        self, symbol: str, pnl_config: PnlCalcConfig, fixed_unit: bool = True
    ) -> None:
        self.outstanding_long_position_list: list[ProxyTrade] = []
        self.outstanding_short_position_list: list[ProxyTrade] = []

        self.archive_long_positions_list: list[ProxyTrade] = []
        self.archive_short_positions_list: list[ProxyTrade] = []

        self.symbol = symbol
        self.enable_short_position = pnl_config.enable_short_position
        self.fixed_unit = fixed_unit
        self.max_position_per_symbol = pnl_config.max_position_per_symbol

        self.stop_loss:float = pnl_config.stoploss

        self.mtm_history = {
            "timestamp": [], #Integer in ms
            "mtm": [] #float
        }

        self.roi_helper = ROI_Helper(pnl_config.roi)
        pass

    def run_at_timestamp(self, dt: datetime, price: float, price_diff:float, buy_sell_action:Buy_Sell_Action_Enum) -> None:
        """ Run the book keeper at a given timestamp

        Args:
            dt (datetime): time stamp
            price (float): price at the timestamp
            price_diff(float): price diff = price(t) - price(t-1
            buy_sell_action (Buy_Sell_Action_Enum): Buy/Sell/Hold
        """

        # 1. Calculate MTM
        accumulated_mtm = 0
        for trade in (self.outstanding_long_position_list + self.outstanding_short_position_list):
            if dt<=trade.entry_datetime or (trade.exit_datetime is not None and trade.exit_datetime<dt):
                logger.debug(f"exclude {trade.entry_datetime} <= {dt}")
                continue
            normalized_mtm = trade.calculate_mtm_normalized(price_diff=price_diff)
            accumulated_mtm += normalized_mtm
        self.mtm_history["timestamp"].append(convert_datetime_to_ms(dt))
        self.mtm_history["mtm"].append(accumulated_mtm)

        # 2. Check if we need to close any position with ROI in each trade
        # a. Long position
        self._check_if_roi_close_position(
            price=price,
            dt=dt,
            live_positions=self.outstanding_long_position_list,
            archive_positions=self.archive_long_positions_list,
        )
        # b. Short position
        self._check_if_roi_close_position(
            price=price,
            dt=dt,
            live_positions=self.outstanding_short_position_list,
            archive_positions=self.archive_short_positions_list,
        )

        #3. Check if we need to close any position with stop/loss in each trade
        # a. Long position
        self._check_if_stop_loss_close_position(
            price=price,
            dt=dt,
            live_positions=self.outstanding_long_position_list,
            archive_positions=self.archive_long_positions_list,
        )
        # b. Short position
        self._check_if_stop_loss_close_position(
            price=price,
            dt=dt,
            live_positions=self.outstanding_short_position_list,
            archive_positions=self.archive_short_positions_list,
        )

        #4. Check if we need to open any position with s(t) and p(t) with buy signal
        if buy_sell_action == Buy_Sell_Action_Enum.BUY:
            self._check_if_open_buy_position(
                price=price,
                dt=dt,
                live_long_positions=self.outstanding_long_position_list,
                live_short_positions=self.outstanding_short_position_list,
                archive_short_positions=self.archive_long_positions_list
            )
        elif buy_sell_action == Buy_Sell_Action_Enum.SELL:
            self._check_if_open_sell_position(
                price=price,
                dt=dt,
                live_short_positions=self.outstanding_short_position_list,
                live_long_positions=self.outstanding_long_position_list,
                archive_long_positions=self.archive_long_positions_list
            )
        pass

    def _check_if_roi_close_position(self, price: float, dt: datetime, live_positions:list[ProxyTrade], archive_positions:list[ProxyTrade]) -> None:
       
        """ Check if we can close the position with ROI

        Args:
            price (float): price at the timestamp
            dt (datetime): time stamp
            live_positions (list[ProxyTrade]): Live position list
            archive_positions (list[ProxyTrade]): archive position list
        """
        for trade in live_positions:
            cur_pnl:float = trade.calculate_pnl_normalized(price = price)
            if self.roi_helper.can_take_profit(entry_date=trade.entry_datetime,current_date=dt, normalized_pnl=cur_pnl):
                # Close the trade
                logger.info(f"Close trade with ROI:{trade}")
                self._close_trade_position_helper(
                    trade=trade,
                    price=price,
                    dt=dt,
                    archive_positions=archive_positions,
                    live_positions=live_positions,
                    close_reason=Proxy_Trade_Actions.ROI
                )
                

        pass

    def _check_if_stop_loss_close_position(self, price: float, dt: datetime, live_positions:list[ProxyTrade], archive_positions:list[ProxyTrade]) -> None:
        """ Check if we can close the position with stop/loss

        Args:
            price (float): price at the timestamp
            dt (datetime): time stamp
            live_positions (list[ProxyTrade]): Live position list
            archive_positions (list[ProxyTrade]): archive position list
        """
        for trade in live_positions:
            cur_pnl:float = trade.calculate_pnl_normalized(price = price)

            if cur_pnl < -(abs(self.stop_loss)):
                # Close the trade
                logger.info(f"Close trade with stop loss:{trade}  at price {price} pnl:{cur_pnl} - {self.stop_loss}")
                
                self._close_trade_position_helper(
                    trade=trade,
                    price=price,
                    dt=dt,
                    archive_positions=archive_positions,
                    live_positions=live_positions,
                    close_reason=Proxy_Trade_Actions.STOP_LOSS
                )
        pass

    def _check_if_open_buy_position(
        self,
        price: float,   
        dt: datetime,
        live_long_positions:list[ProxyTrade],
        live_short_positions:list[ProxyTrade],
        archive_short_positions:list[ProxyTrade]
        )->None:
        """ Check if we can open a long position
        Args:
            price (float): price at the timestamp
            dt (datetime): time stamp
            live_long_positions (list[ProxyTrade]): Live long position list
            live_short_positions (list[ProxyTrade]): Live short position list
            archive_short_positions (list[ProxyTrade]): archive short position list
        """

        # 1. Check if we reach max position
        if len(live_long_positions) >= self.max_position:
            logger.info(f"Reach max position {self.max_position}")
            return

        # 2. Credit line checking: Check if we have enough cash to open a position
        # ignored right now

        # 3. Check if we have any short position to close
        if len(live_short_positions) > 0:
            trade:ProxyTrade = self.get_short_trade_to_close()
            trade.close_position(
                exit_price=price,
                exit_datetime=dt,
                close_reason=Proxy_Trade_Actions.SIGNAL
            )
            self.archive_short_positions_list.append(trade)
            self.outstanding_short_position_list.remove(trade)

            

        pass

    def calculate_mtm(self) -> float:
        """ calculate MTM recorded in the history

        Returns:
            float: total pnl
        """
        mtm_history = self.mtm_history
        mtm_array = np.array(mtm_history["mtm"])
        return mtm_array.sum()
        
    
    def _close_trade_position_helper(self, trade:ProxyTrade, close_reason:Proxy_Trade_Actions,  price:float, dt:datetime, live_positions:list[ProxyTrade], archive_positions:list[ProxyTrade]):
        """  Helper function to close a long position
        

        Args:
            trade (ProxyTrade): trade to close
            close_reason (Proxy_Trade_Actions): close reason
            price (float): close at price
            dt (datetime): close at time
            live_positions (list[ProxyTrade]): live position list
            archive_positions (list[ProxyTrade]): archive position list
        """
        trade.close_position(
            exit_price=price,
            exit_datetime=dt,
            close_reason=close_reason
        )
        archive_positions.append(trade)
        live_positions.remove(trade)
        pass