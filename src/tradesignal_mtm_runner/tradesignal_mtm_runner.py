"""Main module."""
from __future__ import annotations
import os
from .interfaces import ITradeSignalRunner
import pandas as pd

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

    For each position,
    mtm diff = price(t) - price(t-1)
    mtm = mtm diff / (entry price) * 100 (normalized mtm value)
    cum_mtm is the cumulation of mtm number up to t
    cum_mtm += mtm
    max_pnl = max(max_pnl, cum_mtm)
    max_drawdown = max(max_drawdown, max_pnl - cum_mtm)
    mark the pnl_ratio record into the time record

    add up all positions at each t, 
    mtm[t]  = sum(mtm[p,t] for all p)
    cum_mtm[t] = sum(cum_mtm[p,t] for all p)

    calculate the SHARPE ratio based on the pnl_ratio time series
    """

    def __init__(self) -> None:
        super().__init__()

    def calculate(self, symbol: str, buy_signal_dataframe: pd.DataFrame, sell_signal_dataframe: pd.DataFrame) -> Mtm_Result:
        return super().calculate(symbol, buy_signal_dataframe, sell_signal_dataframe)
