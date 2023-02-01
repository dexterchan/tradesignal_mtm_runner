#!/usr/bin/env python
from tradesignal_mtm_runner.models import ProxyTrade, PnlCalcConfig
"""Tests for `tradesignal_mtm_runner` package."""
import numpy as np
import pytest
from functools import reduce
import pandas as pd

from tradesignal_mtm_runner.runner import Trade_Mtm_Runner


test_exchange = "kraken"
test_symbol = "ETHUSD"
test_cases: list = [
    "ascending",
    "descending",
    "take_profit",
    "stop_loss",
    "init",
    "pnl_config_test",
    "ascending_buy_3_signals_sell_1_signal",
]
DATA_DIM = 3000

@pytest.mark.skipif("ascending" not in test_cases, reason="skipped")
def test_trade_pnl_runner_with_ascending_data(get_test_ascending_mkt_data, get_pnl_calculator) -> None:
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM)

    # Buy at row 2 and sell at row 80
    buy_signal = test_mktdata.copy()
    buy_signal["buy"] = np.where(test_mktdata["inx"] == 2, 1, np.nan)
    sell_signal = test_mktdata.copy()
    sell_signal["sell"] = np.where(test_mktdata["inx"] == 80, 1, np.nan)
    pnl = (
        test_mktdata.iloc[80]["close"] - test_mktdata.iloc[2]["close"]
    ) / test_mktdata.iloc[2]["close"]

    pnl_runner = get_pnl_calculator(
        exchange=test_exchange,
        enable_short_position=False,
    )
    pnl_result: PnlCalcConfig = pnl_runner.calculate(
        symbol=test_symbol,
        buy_signal_dataframe=buy_signal,
        sell_signal_dataframe=sell_signal,
    )
    assert (
        pnl_result.pnl == pnl
    ), "pnl not consistent in Buy at row 2 and sell at row 80"
    assert pnl_result.max_drawdown == 0, "max drawdown should be 0"
    assert (
        reduce(lambda x, y: x + y, pnl_result.pnl_timeline["pnl_ratio"])
        == pnl
        == pnl_result.pnl
    )

    pos: ProxyTrade = pnl_result.long_trades_archive[0]

    assert pos.entry_datetime == test_mktdata.iloc[2].name.to_pydatetime()
    assert pos.exit_datetime == test_mktdata.iloc[80].name.to_pydatetime()
    assert pnl_result.sharpe_ratio > 0
    # logger.info(pnl_result.json)
    pass

