
from tradesignal_mtm_runner.trade_reward import TradeBookKeeperAgent
from tradesignal_mtm_runner.config import PnlCalcConfig
from tradesignal_mtm_runner.models import Buy_Sell_Action_Enum, ProxyTrade, LongShort_Enum, Inventory_Mode, Proxy_Trade_Actions
import numpy as np
import pandas as pd
DATA_DIM_MIN = 100
DATA_MOVEMENT = 100
from datetime import datetime, timedelta
import pytest
import logging

logger = logging.getLogger(__name__)

test_symbol="ETHUSD"

def get_trade_agent(pnl_config:PnlCalcConfig) -> TradeBookKeeperAgent:
    return TradeBookKeeperAgent(
        symbol="ETHUSD",
        pnl_config=pnl_config,
        fixed_unit=True
    )
test_cases = [
    "roi_not_close_long_position",
    "roi_close_long_position",
    "roi_not_close_short_position",
    "roi_close_short_position"
]

@pytest.mark.skipif("roi_not_close_long_position" not in test_cases, reason="skipped")
def test_roi_not_close_long_position(get_test_ascending_mkt_data) -> None:
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    #print(test_mktdata)
    pnl_config = PnlCalcConfig.get_default()
    inx = 3
    pnl_config.roi = {
        inx: ((inx)*DATA_MOVEMENT+1000.0+1)/1000.0 - 1
    }

    trade_book_keeper_agent : TradeBookKeeperAgent = get_trade_agent(pnl_config)

    trade_book_keeper_agent.outstanding_long_position_list.append(
        ProxyTrade(
            symbol=test_symbol,
            entry_price=test_mktdata["close"][0],
            entry_datetime=test_mktdata.index[0],
            unit=100,
            direction=LongShort_Enum.LONG,
            inventory_mode=Inventory_Mode.FIFO
        )
    )
    time = test_mktdata.index[inx]
    trade_book_keeper_agent.run_at_timestamp(
        dt=time,
        price = test_mktdata["close"][inx],
        buy_sell_action=Buy_Sell_Action_Enum.HOLD
    )
    assert len(trade_book_keeper_agent.outstanding_long_position_list)==1
    assert trade_book_keeper_agent.outstanding_long_position_list[0].is_closed == False
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 0

@pytest.mark.skipif("roi_close_long_position" not in test_cases, reason="skipped")
def test_roi_close_long_position(get_test_ascending_mkt_data) -> None:
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    #print(test_mktdata)
    pnl_config = PnlCalcConfig.get_default()
    inx = 3
    pnl_config.roi = {
        inx: ((inx)*DATA_MOVEMENT-1)/test_mktdata["close"][0]
    }

    trade_book_keeper_agent : TradeBookKeeperAgent = get_trade_agent(pnl_config)

    trade_book_keeper_agent.outstanding_long_position_list.append(
        ProxyTrade(
            symbol=test_symbol,
            entry_price=test_mktdata["close"][0],
            entry_datetime=test_mktdata.index[0],
            unit=100,
            direction=LongShort_Enum.LONG,
            inventory_mode=Inventory_Mode.FIFO
        )
    )
    time = test_mktdata.index[inx]
    trade_book_keeper_agent.run_at_timestamp(
        dt=time,
        price = test_mktdata["close"][inx],
        buy_sell_action=Buy_Sell_Action_Enum.HOLD
    )
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    assert trade_book_keeper_agent.archive_long_positions_list[0].is_closed
    assert trade_book_keeper_agent.archive_long_positions_list[0].close_reason == Proxy_Trade_Actions.ROI
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 0

    # l = [i for i in range(100)]
    # for i in l :
    #     if i==20 :
    #         l.remove(i)
    # assert len(l)  == 99
    # assert 20 not in l
    # assert 21 in l
    # assert 30 in l

@pytest.mark.skipif("roi_not_close_short_position" not in test_cases, reason="skipped")
def test_roi_not_close_short_position(get_test_ascending_mkt_data) -> None:
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    #print(test_mktdata)
    pnl_config = PnlCalcConfig.get_default()
    inx = 3
    pnl_config.roi = {
        inx: ((inx)*DATA_MOVEMENT-1)/test_mktdata["close"][0]
    }

    trade_book_keeper_agent : TradeBookKeeperAgent = get_trade_agent(pnl_config)

    trade_book_keeper_agent.outstanding_short_position_list.append(
        ProxyTrade(
            symbol=test_symbol,
            entry_price=test_mktdata["close"][0],
            entry_datetime=test_mktdata.index[0],
            unit=100,
            direction=LongShort_Enum.SHORT,
            inventory_mode=Inventory_Mode.FIFO
        )
    )
    time = test_mktdata.index[inx]
    trade_book_keeper_agent.run_at_timestamp(
        dt=time,
        price = test_mktdata["close"][inx],
        buy_sell_action=Buy_Sell_Action_Enum.HOLD
    )
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 1
    assert not trade_book_keeper_agent.outstanding_short_position_list[0].is_closed
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    

@pytest.mark.skipif("roi_close_short_position" not in test_cases, reason="skipped")
def test_roi_close_short_position(get_test_descending_mkt_data) -> None:
    test_mktdata: pd.DataFrame = get_test_descending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    #print(test_mktdata)
    pnl_config = PnlCalcConfig.get_default()
    inx = 3
    pnl_config.roi = {
        inx: ((inx)*DATA_MOVEMENT-1)/test_mktdata["close"][0]
    }

    trade_book_keeper_agent : TradeBookKeeperAgent = get_trade_agent(pnl_config)
    trade_book_keeper_agent.outstanding_short_position_list.append(
        ProxyTrade(
            symbol=test_symbol,
            entry_price=test_mktdata["close"][0],
            entry_datetime=test_mktdata.index[0],
            unit=100,
            direction=LongShort_Enum.SHORT,
            inventory_mode=Inventory_Mode.FIFO
        )
    )
    logger.info(test_mktdata["close"][inx])
    logger.info(trade_book_keeper_agent.outstanding_short_position_list[0].entry_price)
    #logger.info(test_mktdata["close"][inx] - trade_book_keeper_agent.outstanding_short_position_list[0].entry_price)

    time = test_mktdata.index[inx]
    trade_book_keeper_agent.run_at_timestamp(
        dt=time,
        price = test_mktdata["close"][inx],
        buy_sell_action=Buy_Sell_Action_Enum.HOLD
    )
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 0
    assert trade_book_keeper_agent.archive_short_positions_list[0].is_closed
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    pass

