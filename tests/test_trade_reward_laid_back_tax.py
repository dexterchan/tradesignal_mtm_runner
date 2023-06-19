from tradesignal_mtm_runner.trade_reward import TradeBookKeeperAgent
from tradesignal_mtm_runner.config import PnlCalcConfig
from tradesignal_mtm_runner.models import (
    Buy_Sell_Action_Enum,
    ProxyTrade,
    LongShort_Enum,
    Inventory_Mode,
    Proxy_Trade_Actions,
)

import numpy as np
import pandas as pd

DATA_DIM_MIN = 1000
DATA_MOVEMENT = 100
COMPARE_ERROR = 0.01
from datetime import datetime, timedelta
import pytest
import logging

logger = logging.getLogger(__name__)

test_symbol = "ETHUSD"
LAID_BACK_TAX: float = 0.1


def test_laid_back_tax_without_any_position_with_flat_data(
    get_test_flat_mkt_data, get_test_pnl_calc_config
) -> None:
    pnl_calc_config: PnlCalcConfig = get_test_pnl_calc_config()
    pnl_calc_config.laid_back_tax = LAID_BACK_TAX

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_calc_config,
        symbol=test_symbol,
    )

    test_mktdata: pd.DataFrame = get_test_flat_mkt_data(dim=DATA_DIM_MIN)

    # Expected MTM
    expected_mtm: float = len(test_mktdata) * -LAID_BACK_TAX

    for i in range(DATA_DIM_MIN):
        action: Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.HOLD

        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action,
        )

    assert (
        abs(expected_mtm - np.sum(trade_book_keeper_agent.mtm_history_value))
        < COMPARE_ERROR
    ), f"expected_mtm: {expected_mtm} - accum mtm{np.sum(trade_book_keeper_agent.mtm_history_value)}"

    pass


def test_laid_back_tax_with_long_position_with_flat_data(
    get_test_flat_mkt_data, get_test_pnl_calc_config
) -> None:
    pnl_calc_config: PnlCalcConfig = get_test_pnl_calc_config(
        fee_rate=0, laid_back_tax=LAID_BACK_TAX
    )

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_calc_config,
        symbol=test_symbol,
    )

    start_buy_inx = DATA_DIM_MIN // 2
    end_buy_inx = start_buy_inx + DATA_DIM_MIN // 3

    # load market data
    test_mktdata: pd.DataFrame = get_test_flat_mkt_data(DATA_DIM_MIN)

    # Expected MTM
    expected_mtm: float = (
        len(test_mktdata) - (end_buy_inx - start_buy_inx)
    ) * -LAID_BACK_TAX

    # Iterate market data
    for i in range(DATA_DIM_MIN):
        action: Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.HOLD

        if i == start_buy_inx:
            action = Buy_Sell_Action_Enum.BUY
        elif i == end_buy_inx:
            action = Buy_Sell_Action_Enum.SELL

        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action,
        )
    assert (
        abs(expected_mtm - np.sum(trade_book_keeper_agent.mtm_history_value))
        < COMPARE_ERROR
    ), f"expected_mtm: {expected_mtm} - accum mtm{np.sum(trade_book_keeper_agent.mtm_history_value)}"

    pass


def laidbacktax_with_short_position_with_flat_data(
    get_test_flat_mkt_data, get_test_pnl_calc_config
) -> None:
    pnl_calc_config: PnlCalcConfig = get_test_pnl_calc_config(
        fee_rate=0, laid_back_tax=LAID_BACK_TAX
    )

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_calc_config,
        symbol=test_symbol,
    )

    start_sell_inx = DATA_DIM_MIN // 2
    end_sell_inx = start_sell_inx + DATA_DIM_MIN // 3

    # load market data
    test_mktdata: pd.DataFrame = get_test_flat_mkt_data(DATA_DIM_MIN)

    # Expected MTM
    expected_mtm: float = (
        len(test_mktdata) - (end_sell_inx - start_sell_inx)
    ) * -LAID_BACK_TAX

    # Iterate market data
    for i in range(DATA_DIM_MIN):
        action: Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.HOLD

        if i == start_sell_inx:
            action = Buy_Sell_Action_Enum.SELL
        elif i == end_sell_inx:
            action = Buy_Sell_Action_Enum.BUY

        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action,
        )

    assert (
        abs(expected_mtm - np.sum(trade_book_keeper_agent.mtm_history_value))
        < COMPARE_ERROR
    ), f"expected_mtm: {expected_mtm} - accum mtm{np.sum(trade_book_keeper_agent.mtm_history_value)}"

    pass
