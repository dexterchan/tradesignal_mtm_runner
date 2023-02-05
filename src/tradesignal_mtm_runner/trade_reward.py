from __future__ import annotations
from .config import PnlCalcConfig
from .models import ProxyTrade, Buy_Sell_Action_Enum, Proxy_Trade_Actions
from .helper import ROI_Helper
from datetime import datetime
from .utility import convert_datetime_to_ms
import logging

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
                trade.close_position(
                    exit_price=price,
                    exit_datetime=dt,
                    close_reason=Proxy_Trade_Actions.ROI
                )
                archive_positions.append(trade)
                live_positions.remove(trade)

        pass