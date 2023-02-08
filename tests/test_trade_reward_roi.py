
from tradesignal_mtm_runner.trade_reward import TradeBookKeeperAgent
from tradesignal_mtm_runner.config import PnlCalcConfig
from tradesignal_mtm_runner.models import Buy_Sell_Action_Enum, ProxyTrade, LongShort_Enum, Inventory_Mode, Proxy_Trade_Actions
import numpy as np
import pandas as pd
DATA_DIM_MIN = 100
DATA_MOVEMENT = 100
COMPARE_ERROR = 0.00001
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
    "mtm_history_consistency_with_close_trade",
    "mtm_history_consistency",
    "roi_not_close_long_position",
    "roi_close_long_position",
    "roi_not_close_short_position",
    "roi_close_short_position"
]

def calculate_pnl_from_mtm_history(trade_book_keeper_agent:TradeBookKeeperAgent) -> float:
    mtm_history = trade_book_keeper_agent.mtm_history
    mtm_array = np.array(mtm_history["mtm"])
    return mtm_array.sum()

@pytest.mark.skipif("mtm_history_consistency_with_close_trade" not in test_cases, reason="skipped")
def test_mtm_history_consistency_with_close_trade(get_test_ascending_mkt_data) -> None:
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    #print(test_mktdata)
    pnl_config = PnlCalcConfig.get_default()
    start_index = 1
    end_index = 9
    
    pnl_config.roi = {
        end_index: 1000
    }
    trade_book_keeper_agent : TradeBookKeeperAgent = get_trade_agent(pnl_config)

    p1:ProxyTrade = ProxyTrade(
            symbol=test_symbol,
            entry_price=test_mktdata["close"][start_index],
            entry_datetime=test_mktdata.index[start_index],
            unit=100,
            direction=LongShort_Enum.LONG,
            inventory_mode=Inventory_Mode.FIFO
        )
    
    

    for i in range(0, len(test_mktdata)):
        if test_mktdata.index[i] == test_mktdata.index[start_index]:
            trade_book_keeper_agent.outstanding_long_position_list.append(p1)
        if i == end_index:
            p1.close_position(exit_price=test_mktdata["close"][end_index],
                      exit_datetime=test_mktdata.index[end_index],
                      close_reason=Proxy_Trade_Actions.SIGNAL)
            trade_book_keeper_agent.archive_long_positions_list.append(p1)
            trade_book_keeper_agent.outstanding_long_position_list.remove(p1)
            
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=Buy_Sell_Action_Enum.HOLD
        )
    accumulated_pnl:float = 0
    for trade in trade_book_keeper_agent.archive_long_positions_list:
        accumulated_pnl += trade.calculate_pnl_normalized(trade.exit_price)
    assert accumulated_pnl == (trade.exit_price - trade.entry_price)/trade.entry_price
    # logger.debug(trade.exit_price)
    # logger.debug(trade.entry_price)
    # logger.debug(trade_book_keeper_agent.mtm_history["mtm"])
    assert (calculate_pnl_from_mtm_history(trade_book_keeper_agent) - accumulated_pnl) < COMPARE_ERROR


    pass

@pytest.mark.skipif("mtm_history_consistency" not in test_cases, reason="skipped")
def test_mtm_history_consistency(get_test_ascending_mkt_data) -> None:
    
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    #print(test_mktdata)
    pnl_config = PnlCalcConfig.get_default()
    inx = 3
    pnl_config.roi = {
        inx: 1000
    }
    trade_book_keeper_agent : TradeBookKeeperAgent = get_trade_agent(pnl_config)

    p1:ProxyTrade = ProxyTrade(
            symbol=test_symbol,
            entry_price=test_mktdata["close"][0],
            entry_datetime=test_mktdata.index[0],
            unit=100,
            direction=LongShort_Enum.LONG,
            inventory_mode=Inventory_Mode.FIFO
        )
    p2:ProxyTrade = ProxyTrade(
            symbol=test_symbol,
            entry_price=test_mktdata["close"][inx],
            entry_datetime=test_mktdata.index[inx],
            unit=100,
            direction=LongShort_Enum.LONG,
            inventory_mode=Inventory_Mode.FIFO
        )
    
    

    for i in range(0, test_mktdata.shape[0]):
        if test_mktdata.index[i] == test_mktdata.index[0]:
            trade_book_keeper_agent.outstanding_long_position_list.append(p1)
        if test_mktdata.index[inx] == test_mktdata.index[i]:
            trade_book_keeper_agent.outstanding_long_position_list.append(p2)
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=Buy_Sell_Action_Enum.HOLD
        )
    accumulated_pnl:float = 0
    for trade in trade_book_keeper_agent.outstanding_long_position_list:
        accumulated_pnl += trade.calculate_pnl_normalized(test_mktdata["close"][-1])
    #print(trade_book_keeper_agent.mtm_history)
    #print(trade_book_keeper_agent.outstanding_long_position_list)
    assert len(trade_book_keeper_agent.outstanding_long_position_list)==2
    assert (calculate_pnl_from_mtm_history(trade_book_keeper_agent) - accumulated_pnl) < COMPARE_ERROR

    
    pass


@pytest.mark.skipif("roi_not_close_long_position" not in test_cases, reason="skipped")
def test_roi_not_close_long_position(get_test_ascending_mkt_data) -> None:
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    #print(test_mktdata)
    pnl_config = PnlCalcConfig.get_default()
    inx = 3
    pnl_config.roi = {
        inx: ((inx)*DATA_MOVEMENT+1)/test_mktdata["close"][0]
    }

    trade_book_keeper_agent : TradeBookKeeperAgent = get_trade_agent(pnl_config)

    p:ProxyTrade = ProxyTrade(
            symbol=test_symbol,
            entry_price=test_mktdata["close"][0],
            entry_datetime=test_mktdata.index[0],
            unit=100,
            direction=LongShort_Enum.LONG,
            inventory_mode=Inventory_Mode.FIFO
        )
    trade_book_keeper_agent.outstanding_long_position_list.append(p)
    
    
    time = test_mktdata.index[inx]
    trade_book_keeper_agent.run_at_timestamp(
        dt=time,
        price = test_mktdata["close"][inx],
        buy_sell_action=Buy_Sell_Action_Enum.HOLD,
        price_diff=test_mktdata["price_movement"][inx],
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

    p = ProxyTrade(
            symbol=test_symbol,
            entry_price=test_mktdata["close"][0],
            entry_datetime=test_mktdata.index[0],
            unit=100,
            direction=LongShort_Enum.LONG,
            inventory_mode=Inventory_Mode.FIFO
        )
    trade_book_keeper_agent.outstanding_long_position_list.append(p)
    time = test_mktdata.index[inx]
    trade_book_keeper_agent.run_at_timestamp(
        dt=time,
        price = test_mktdata["close"][inx],
        buy_sell_action=Buy_Sell_Action_Enum.HOLD,
        price_diff=test_mktdata["price_movement"][inx],
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
    DATA_DIM_MIN = 10
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    #print(test_mktdata)
    pnl_config = PnlCalcConfig.get_default()
    inx = 3
    pnl_config.roi = {
        inx: ((inx)*DATA_MOVEMENT-1)/test_mktdata["close"][0]
    }

    trade_book_keeper_agent : TradeBookKeeperAgent = get_trade_agent(pnl_config)

    p = ProxyTrade(
            symbol=test_symbol,
            entry_price=test_mktdata["close"][0],
            entry_datetime=test_mktdata.index[0],
            unit=100,
            direction=LongShort_Enum.SHORT,
            inventory_mode=Inventory_Mode.FIFO
        )
    trade_book_keeper_agent.outstanding_short_position_list.append(p)
    for i in range(len(test_mktdata)):
        time = test_mktdata.index[i]
        trade_book_keeper_agent.run_at_timestamp(
            dt=time,
            price = test_mktdata["close"][i],
            buy_sell_action=Buy_Sell_Action_Enum.HOLD,
            price_diff=test_mktdata["price_movement"][i],
        )
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 1
    assert not trade_book_keeper_agent.outstanding_short_position_list[0].is_closed
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    #Verify Pnl
    logger.info(trade_book_keeper_agent.outstanding_short_position_list)
    correct_pnl_normalized:float = p.calculate_pnl_normalized(test_mktdata["close"][-1])
    assert (calculate_pnl_from_mtm_history(trade_book_keeper_agent) - correct_pnl_normalized) < COMPARE_ERROR
    

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

    p = ProxyTrade(
            symbol=test_symbol,
            entry_price=test_mktdata["close"][0],
            entry_datetime=test_mktdata.index[0],
            unit=100,
            direction=LongShort_Enum.SHORT,
            inventory_mode=Inventory_Mode.FIFO
        )
    trade_book_keeper_agent.outstanding_short_position_list.append(p)
    logger.debug(test_mktdata["close"][inx])
    logger.debug(trade_book_keeper_agent.outstanding_short_position_list[0].entry_price)
    #logger.info(test_mktdata["close"][inx] - trade_book_keeper_agent.outstanding_short_position_list[0].entry_price)

    time = test_mktdata.index[inx]
    trade_book_keeper_agent.run_at_timestamp(
        dt=time,
        price = test_mktdata["close"][inx],
        buy_sell_action=Buy_Sell_Action_Enum.HOLD,
        price_diff=test_mktdata["price_movement"][inx],
    )
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 0
    assert trade_book_keeper_agent.archive_short_positions_list[0].is_closed
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    
