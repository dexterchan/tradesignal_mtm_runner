"""Main module."""
from __future__ import annotations
import os
from .interfaces import ITradeSignalRunner
import pandas as pd
from models import Mtm_Result, ProxyTrade

class Mtm_Runner(ITradeSignalRunner):
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
    
    
    calculate the SHARPE ratio based on the mtm time series
    """

    def __init__(self) -> None:
        super().__init__()

    def calculate(self, symbol: str, buy_signal_dataframe: pd.DataFrame, sell_signal_dataframe: pd.DataFrame) -> Mtm_Result:
        """[summary]

        Args:
            symbol (str): [description]
            buy_signal_dataframe (pd.DataFrame): [description]
            sell_signal_dataframe (pd.DataFrame): [description]

        Returns:
            Mtm_Result: [description]
        """

        _signal_dataframe: pd.DataFrame = buy_signal_dataframe
        _signal_dataframe["sell"] = sell_signal_dataframe["sell"]

        return super().calculate(symbol, buy_signal_dataframe, sell_signal_dataframe)
    
    def _iterate_each_timeframe_generate_trade_positions(
        self,
        symbol: str,
        signal_dataframe: pd.DataFrame,
    ) -> list[ProxyTrade]:
        """_summary_

        Args:
            symbol (str): _description_
            signal_dataframe (pd.DataFrame): _description_

        Returns:
            list[ProxyTrade]: _description_
        """
        # convert dataframe to numpy array in the data format of float
        close_price = signal_dataframe["close"].to_numpy(dtype=float)
        buy_signal = signal_dataframe["buy"].to_numpy(dtype=int)
        sell_signal = signal_dataframe["sell"].to_numpy(dtype=int)
        time_line = signal_dataframe.index.to_numpy(dtype="datetime64")

        return []
