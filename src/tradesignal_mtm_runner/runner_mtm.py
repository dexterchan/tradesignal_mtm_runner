from __future__ import annotations
from .interfaces import ITradeSignalRunner
from .config import PnlCalcConfig
from .helper import ROI_Helper

from .trade_order import TradeOrderSimulator
from .models import Mtm_Result

import pandas as pd
import logging

logger = logging.getLogger(__name__)

class Trade_Mtm_Runner(ITradeSignalRunner):
    """Accept buy/sell signal from Strategy
    buy/sell signal should be coupled with market data from panda dataframe
    stop loss/profit checker also initialized into the runner.
    Note: it will merage buy + sell signal into one dataframe when processing

    to reduce complexity, we assume trade is fully filled each time

    mtm runner will generate pnl time series
    for each time record, up to t,  do the following:
    1) calculate the mtm based on the position 
    2) apply buy/sell signals -> update the trade position
    3) check if stop loss/profit required -> if yes, close the trade and update trade position
    Finally, we can conclude the Pnl by adding up all the mtm

    reference: MTM calculation - https://ibkr.info/node/56
    price diff[t] = price(t) - price(t-1)
    For each position[p] in each candlestick[t]:
        mtm[p][t] = price diff[t] / (entry price[p]) * 100 (normalized mtm value)
        #cum_mtm[p][t] is the cumulation of mtm number up to t
        cum_mtm[p][t] += mtm[p][t]
    mtm[t] = [mtm[p] for all p]
    cum_mtm[t] = [ cum_mtm[p][t] for all p]
    max_pnl = max(max_pnl, cum_mtm[t])
    max_drawdown = max(max_drawdown, max_pnl - cum_mtm[t])
    """
    def __init__(
        self,
        pnl_config: PnlCalcConfig,
    ) -> None:
        """
        Args:
            enable_short_position (bool): enable short position
            fixed_unit_amount (float): stake amount
            no_duplicate_trade (bool, optional): no duplication for the same symbol. Defaults to True.
        """

        self._take_profit: float = pnl_config.roi[0]  # (take_profit_pct/100.0)
        self._roi: dict[int, float] = pnl_config.roi
        self._stop_loss: float = pnl_config.stoploss  # (- stop_loss_pct/100.0)
        self.enable_short_position = pnl_config.enable_short_position
        self.fix_unit_amount = pnl_config.fixed_stake_unit_amount
        self.pnl_config = pnl_config
        self.PROFIT_SLIPPAGE: float = 0.00005

        self._roi_helper = ROI_Helper(roi_dict=self._roi)
        logger.debug(
            f"Take profit at {self._take_profit} ; Stop Loss at {self._stop_loss}"
        )
        # Potential to support multiple symbols in the pnl run.
        self.trade_order_keeper_map: dict[str, TradeOrderSimulator] = {}
        pass

    
    def calculate(
        self,
        symbol: str,
        buy_signal_dataframe: pd.DataFrame,
        sell_signal_dataframe: pd.DataFrame,
    ) -> Mtm_Result:
        """[summary]

        Args:
            symbol (str): [description]
            buy_signal_dataframe (pd.DataFrame): [description]
            sell_signal_dataframe (pd.DataFrame): [description]

        Returns:
            Mtm_Result: [description]
        """
        _signal_dataframe: pd.DataFrame = self._prepare_df_for_analysis(
            buy_signal_dataframe=buy_signal_dataframe,
            sell_signal_dataframe=sell_signal_dataframe
        )
        
        return self._iterate_each_timeframe(
            symbol=symbol, signal_dataframe=_signal_dataframe
        )

    def _prepare_df_for_analysis(self,buy_signal_dataframe: pd.DataFrame,
        sell_signal_dataframe: pd.DataFrame, ) -> pd.DataFrame:
        """
        Prepare the dataframe for analysis
    

        Args:
            buy_signal_dataframe (pd.DataFrame): buy data frame "close price", "buy" column
            sell_signal_dataframe (pd.DataFrame): sell data frame  "close price" "sell column

        Returns:
            pd.DataFrame: _description_
        """
        _signal_dataframe: pd.DataFrame = buy_signal_dataframe
        _signal_dataframe["sell"] = sell_signal_dataframe["sell"]
        _signal_dataframe["price_movement"] = _signal_dataframe["close"].diff(1)

        return _signal_dataframe