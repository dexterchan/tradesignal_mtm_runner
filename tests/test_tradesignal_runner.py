#!/usr/bin/env python
from __future__ import annotations
"""Tests for `tradesignal_mtm_runner` package."""
import numpy as np
import pytest
from functools import reduce
import pandas as pd

from tradesignal_mtm_runner.config import PnlCalcConfig
from tradesignal_mtm_runner.models import ProxyTrade , Mtm_Result, MIN_NUMERIC_VALUE

from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger(__name__)

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

@pytest.fixture()
def _get_pnl_config_single_position_per_symbol() -> PnlCalcConfig:
    def _position(pos: int) -> PnlCalcConfig:
        pnl_config = PnlCalcConfig.get_default()
        pnl_config.max_position_per_symbol = pos
        return pnl_config

    return _position

@pytest.mark.skipif("ascending" not in test_cases, reason="skipped")
def test_trade_pnl_runner_with_ascending_data(get_test_ascending_mkt_data,get_pnl_calculator) -> None:
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

@pytest.mark.skipif("descending" not in test_cases, reason="skipped")
def test_trade_pnl_runner_with_descending_data(get_test_descending_mkt_data,get_pnl_calculator) -> None:
    test_mktdata: pd.DataFrame = get_test_descending_mkt_data(dim=DATA_DIM)

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
    pnl_result: Mtm_Result = pnl_runner.calculate(
        symbol=test_symbol,
        buy_signal_dataframe=buy_signal,
        sell_signal_dataframe=sell_signal,
    )
    assert pnl_result.pnl == pnl, "pnl not consistent in Buy at 2 and sell at 80"
    assert pnl_result.max_drawdown != 0, "max drawdown should not be 0"
    assert (
        reduce(lambda x, y: x + y, pnl_result.pnl_timeline["pnl_ratio"])
        == pnl
        == pnl_result.pnl
    )
    assert pnl_result.sharpe_ratio > MIN_NUMERIC_VALUE  # float("-inf")

@pytest.mark.skipif("take_profit" not in test_cases, reason="skipped")
def test_trade_pnl_runner_with_take_profit(get_test_ascending_mkt_data, get_pnl_calculator) -> None:
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM)
    # print(test_mktdata)
    # Buy at row 2 and sell at row 80
    buy_signal = test_mktdata.copy()
    buy_signal["buy"] = np.where(test_mktdata["inx"] == 2, 1, np.nan)
    sell_signal = test_mktdata.copy()
    sell_signal["sell"] = np.where(test_mktdata["inx"] == 80, 1, np.nan)
    pnl_without_take_profit = (
        test_mktdata.iloc[80]["close"] - test_mktdata.iloc[2]["close"]
    ) / test_mktdata.iloc[2]["close"]

    buy_price = buy_signal[buy_signal["buy"] == 1]["close"].values[0]
    close_price_without_take_profit = sell_signal[sell_signal["sell"] == 1][
        "close"
    ].values[0]
    profit_pct: float = 10.0
    take_profit_price = buy_price * (1 + profit_pct / 100.00)
    # logger.debug(f"Planned Pnl: buy_price:{buy_price} - take_profit:{take_profit_price}")

    pnlconfig = PnlCalcConfig.get_default()
    pnlconfig.roi[0] = profit_pct / 100
    pnl_runner = get_pnl_calculator(
        exchange=test_exchange, enable_short_position=False, pnl_config=pnlconfig
    )
    pnl_result: Mtm_Result = pnl_runner.calculate(
        symbol=test_symbol,
        buy_signal_dataframe=buy_signal,
        sell_signal_dataframe=sell_signal,
    )
    # logger.debug(f"test Pnl: pnl:{pnl} - {max_dd}")
    assert profit_pct / 100 <= pnl_result.pnl < pnl_without_take_profit
    assert (
        close_price_without_take_profit
        >= pnl_runner.trade_order_keeper_map[test_symbol]
        .archive_long_positions_list[-1]
        .exit_price
        >= take_profit_price
    )
    assert (
        reduce(lambda x, y: x + y, pnl_result.pnl_timeline["pnl_ratio"])
        == pnl_result.pnl
    )
    assert pnl_result.sharpe_ratio > 0
    pass


@pytest.mark.skipif("stop_loss" not in test_cases, reason="skipped")
def test_trade_pnl_runner_with_stop_loss(get_test_descending_mkt_data, get_pnl_calculator) -> None:
    test_mktdata: pd.DataFrame = get_test_descending_mkt_data(dim=DATA_DIM)

    # Buy at row 2 and sell at row 80
    buy_signal = test_mktdata.copy()
    buy_signal["buy"] = np.where(test_mktdata["inx"] == 2, 1, np.nan)
    sell_signal = test_mktdata.copy()
    sell_signal["sell"] = np.where(test_mktdata["inx"] == 80, 1, np.nan)
    pnl_without_stop_loss = (
        test_mktdata.iloc[80]["close"] - test_mktdata.iloc[2]["close"]
    ) / test_mktdata.iloc[2]["close"]
    buy_price = buy_signal[buy_signal["buy"] == 1]["close"].values[0]
    close_price_without_stop_loss = sell_signal[sell_signal["sell"] == 1][
        "close"
    ].values[0]
    logger.info(f"pnl_without_stop_loss:{pnl_without_stop_loss}")

    loss_pct: float = pnl_without_stop_loss / 2  # 10.0
    stop_loss_price = buy_price * (1 - loss_pct / 100.00)
    pnlconfig = PnlCalcConfig.get_default()
    pnlconfig.stoploss = (-1) * loss_pct / 100
    close_price_with_stop_loss = buy_price * (1 + pnlconfig.stoploss)
    logger.info(f"close_price_with_stop_loss:{close_price_with_stop_loss}")

    pnl_runner = get_pnl_calculator(
        exchange=test_exchange, enable_short_position=False, pnl_config=pnlconfig
    )

    pnl_result: Mtm_Result = pnl_runner.calculate(
        symbol=test_symbol,
        buy_signal_dataframe=buy_signal,
        sell_signal_dataframe=sell_signal,
    )

    assert pnl_result.long_trades_archive[0].exit_price > close_price_without_stop_loss
    logger.debug(f"test Pnl: pnl:{pnl_result.pnl} - {pnl_result.max_drawdown}")
    logger.debug(f"close_price_without_stop_loss:{close_price_without_stop_loss}")

    logger.debug(pnl_result.long_trades_archive)

    assert loss_pct / 100 >= pnl_result.pnl > pnl_without_stop_loss
    assert (
        close_price_without_stop_loss
        < pnl_runner.trade_order_keeper_map[test_symbol]
        .archive_long_positions_list[-1]
        .exit_price
        <= stop_loss_price
    )
    assert (
        reduce(lambda x, y: x + y, pnl_result.pnl_timeline["pnl_ratio"])
        == pnl_result.pnl
    )
    assert pnl_result.sharpe_ratio > MIN_NUMERIC_VALUE  # float("-inf")

    obj = pnl_result.dict()
    # logger.info(type(obj))
    logger.info(obj["pnl_daily"])
    logger.info(obj["sharpe_ratio"])
    pass

@pytest.mark.skipif(
    "ascending_buy_3_signals_sell_1_signal" not in test_cases, reason="skipped"
)
def test_duplicated_buy_3_signals_sell_1_signal(
    _get_pnl_config_single_position_per_symbol, get_test_ascending_mkt_data, get_pnl_calculator
) -> None:
    """Test duplicated buy position at the time line"""
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM)

    _pnl_config: PnlCalcConfig = _get_pnl_config_single_position_per_symbol(1)
    _pnl_config.max_position_per_symbol = 10000
    # Buy at row 2 and sell at row 80
    buy_signal = test_mktdata.copy()
    buy_signal_array = [np.nan] * len(test_mktdata)
    buy_signal_array[2] = 1
    buy_signal_array[3] = 1
    buy_signal_array[5] = 1
    buy_signal["buy"] = buy_signal_array
    # buy_signal["buy"] = np.where(
    #     test_mktdata["inx"] == 2, 1, np.nan
    # )
    sell_signal = test_mktdata.copy()
    sell_signal["sell"] = np.where(test_mktdata["inx"] == 80, 1, np.nan)

    buy_signal["pnl"] = (buy_signal["close"][80] - buy_signal["close"]) / buy_signal[
        "close"
    ]
    buy_signal["pnl"] = buy_signal["buy"] * buy_signal["pnl"]
    pnl = buy_signal[buy_signal["pnl"].notnull()]["pnl"].to_list()

    pnl_runner = get_pnl_calculator(
        exchange=test_exchange,
        pnl_config=_pnl_config,
        enable_short_position=False,
    )
    pnl_result: Mtm_Result = pnl_runner.calculate(
        symbol=test_symbol,
        buy_signal_dataframe=buy_signal,
        sell_signal_dataframe=sell_signal,
    )

    assert (
        pnl_result.pnl == pnl[-1]
    ), "pnl not consistent in Buy at row 2 and sell at row 80"
    assert pnl_result.max_drawdown == 0, "max drawdown should be 0"

    assert len(pnl_result.long_trades_outstanding) == 2
    archive_long_position_list: list = pnl_result.long_trades_archive
    pos: ProxyTrade = archive_long_position_list[0]

    assert pos.entry_datetime == test_mktdata.iloc[5].name.to_pydatetime()
    assert pos.exit_datetime == test_mktdata.iloc[80].name.to_pydatetime()
    assert (
        reduce(lambda x, y: x + y, pnl_result.pnl_timeline["pnl_ratio"])
        == pnl_result.pnl
    )
    assert pnl_result.sharpe_ratio > 0
    pass

