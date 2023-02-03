from __future__ import annotations
from .config import PnlCalcConfig
from .models import ProxyTrade, Buy_Sell_Action_Enum
from .helper import ROI_Helper

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
            "timestamp": [],
            "mtm": []
        }

        from .helper import ROI_Helper
        pass

    def run_at_timestamp(self, timestamp: int, price: float, buy_sell_action:Buy_Sell_Action_Enum) -> None:
        """ Run the book keeper at a given timestamp

        Args:
            timestamp (int): time stamp
            price (float): price at the timestamp
            buy_sell_action (Buy_Sell_Action_Enum): Buy/Sell/Hold
        """

        # 1. Calculate MTM
        accumulated_mtm = 0
        for trade in self.outstanding_long_position_list:
            normalized_pnl = trade.calculate_pnl_normalized(price)
            accumulated_mtm += normalized_pnl
        self.mtm_history["timestamp"].append(timestamp)
        self.mtm_history["mtm"].append(accumulated_mtm)

        # 2. Check if we need to close any position with ROI


        pass