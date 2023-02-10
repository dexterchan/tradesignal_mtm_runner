from tradesignal_mtm_runner.trade_reward import TradeBookKeeperAgent
from tradesignal_mtm_runner.config import PnlCalcConfig
from tradesignal_mtm_runner.models import Buy_Sell_Action_Enum, ProxyTrade, LongShort_Enum, Inventory_Mode, Proxy_Trade_Actions
import numpy as np
import pandas as pd
DATA_DIM_MIN = 10 * 2
DATA_MOVEMENT = 100
COMPARE_ERROR = 0.1
from datetime import datetime, timedelta
import pytest
import logging

logger = logging.getLogger(__name__)

test_symbol="ETHUSD"

@pytest.fixture
def get_pnl_config_stoploss() -> PnlCalcConfig:
    def _get_pnl_config_stoploss(expected_stoploss:float) -> PnlCalcConfig:
        pnl_config: PnlCalcConfig = PnlCalcConfig.get_default()
        pnl_config.stoploss = expected_stoploss
        return pnl_config
    return _get_pnl_config_stoploss

test_cases:list = [
    "tradesignal_long_no_roi_no_stoploss",
    "tradesignal_short_no_roi_no_stoploss",
    "tradesignal_long_with_roi",
    "tradesignal_short_with_roi",
    "tradesignal_long_with_stoploss",
    "tradesignal_short_with_stoploss",
    "tradesignal_long_with_short_positions",
    "tradesignal_short_with_long_positions"
]

@pytest.mark.skipif("tradesignal_long_no_roi_no_stoploss" not in test_cases, reason="Not implemented yet")
def test_tradesignal_long_no_roi_no_stoploss(get_test_ascending_mkt_data) -> None:
    """ simple testing of long signal with no stoploss and no roi

    Args:
        get_test_ascending_mkt_data (_type_): _description_
    """
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    #print(test_mktdata)
    start = 5

    pnl_config:PnlCalcConfig = PnlCalcConfig.get_default()

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )
    #Run through the market data
    for i in range(1, len(test_mktdata)):
        action:Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.BUY if i==start else Buy_Sell_Action_Enum.HOLD
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action
        )
    
    #Check the result
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 1
    assert len(trade_book_keeper_agent.archive_long_positions_list) == 0

    accumulated_pnl:float = 0
    for trade in trade_book_keeper_agent.outstanding_long_position_list:
        accumulated_pnl += trade.calculate_pnl_normalized(test_mktdata["close"][-1])
    agent_mtm:float = trade_book_keeper_agent.calculate_mtm()
    assert abs(accumulated_pnl - agent_mtm) < COMPARE_ERROR

@pytest.mark.skipif("tradesignal_short_no_roi_no_stoploss" not in test_cases, reason="Not implemented yet")
def test_tradesignal_short_no_roi_no_stoploss(get_test_descending_mkt_data) -> None:
    """_summary_

    Args:
        get_test_descending_mkt_data (_type_): _description_
    """
    test_mktdata: pd.DataFrame = get_test_descending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    #print(test_mktdata)
    start = 5

    pnl_config:PnlCalcConfig = PnlCalcConfig.get_default()

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )
    #Run through the market data
    for i in range(1, len(test_mktdata)):
        action:Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.SELL if i==start else Buy_Sell_Action_Enum.HOLD
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action
        )
    
    #Check the result
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 1
    assert len(trade_book_keeper_agent.archive_short_positions_list) == 0

    accumulated_pnl:float = 0
    for trade in trade_book_keeper_agent.outstanding_short_position_list:
        accumulated_pnl += trade.calculate_pnl_normalized(test_mktdata["close"][-1])
    agent_mtm:float = trade_book_keeper_agent.calculate_mtm()
    assert abs(accumulated_pnl - agent_mtm) < COMPARE_ERROR

@pytest.mark.skipif("tradesignal_long_with_roi" not in test_cases, reason="Not implemented yet")
def test_tradesignal_long_with_roi(get_test_ascending_mkt_data) -> None:
    """ simple testing of long signal with roi

    Args:
        get_test_ascending_mkt_data (_type_): _description_
    """
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    print(test_mktdata)
    pnl_config = PnlCalcConfig.get_default()
    inx:int = int(DATA_DIM_MIN/4)
    
    pnl_length:int = int(DATA_DIM_MIN/5)

    pnl_config.roi = {
        inx: ((pnl_length)*DATA_MOVEMENT)/test_mktdata["close"][0]
    }
    expect_mtm:float = (pnl_length+1)*DATA_MOVEMENT/test_mktdata["close"][inx]

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )

    #Run through the market data
    for i in range( len(test_mktdata)):
        action:Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.BUY if i==inx else Buy_Sell_Action_Enum.HOLD
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action
        )
        if len(trade_book_keeper_agent.outstanding_long_position_list)>0:
            trade = trade_book_keeper_agent.outstanding_long_position_list[0]
            logger.info(f"{i} : {trade.is_closed} : {trade_book_keeper_agent.mtm_history['mtm'][-1]} : {trade.calculate_pnl_normalized(test_mktdata['close'][i])} ")
    #Check the result
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    assert len(trade_book_keeper_agent.archive_long_positions_list) == 1
    logger.info(trade_book_keeper_agent.mtm_history)
    logger.info(pnl_config.roi)
    mtm = trade_book_keeper_agent.calculate_mtm()
    assert abs(mtm - expect_mtm )< DATA_MOVEMENT*2/test_mktdata["close"][0]

    pass

@pytest.mark.skipif("tradesignal_short_with_roi" not in test_cases, reason="Not implemented yet")
def test_tradesignal_short_with_roi(get_test_descending_mkt_data) -> None:
    """ simple testing of short signal with roi

    Args:
        get_test_descending_mkt_data (_type_): _description_
    """
    test_mktdata: pd.DataFrame = get_test_descending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    print(test_mktdata)
    pnl_config = PnlCalcConfig.get_default()
    inx:int = int(DATA_DIM_MIN/4)

    pnl_length:int = int(DATA_DIM_MIN/5)

    pnl_config.roi = {
        inx: ((pnl_length)*DATA_MOVEMENT+1)/test_mktdata["close"][0]
    }
    expect_mtm:float = (pnl_length)*DATA_MOVEMENT/test_mktdata["close"][inx]

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )

    #Run through the market data
    for i in range(1, len(test_mktdata)):
        action:Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.SELL if i==inx else Buy_Sell_Action_Enum.HOLD
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action
        )
    #Check the result
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 0
    assert len(trade_book_keeper_agent.archive_short_positions_list) == 1
    # logger.info(trade_book_keeper_agent.mtm_history)
    # logger.info(pnl_config.roi)
    mtm = trade_book_keeper_agent.calculate_mtm()
    assert abs(mtm - expect_mtm )< DATA_MOVEMENT/test_mktdata["close"][inx]

    pass

@pytest.mark.skipif("tradesignal_long_with_stoploss" not in test_cases, reason="Not implemented yet")
def test_tradesignal_long_with_stoploss(get_test_descending_mkt_data, get_pnl_config_stoploss) -> None:
    """ simple testing of long signal with stoploss

    Args:
        get_test_descending_mkt_data (_type_): _description_
    """
    test_mktdata: pd.DataFrame = get_test_descending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    pnl_config = PnlCalcConfig.get_default()
    start:int = int(DATA_DIM_MIN/4)
    end:int = start + int(DATA_DIM_MIN/5)
    
    expected_loss = (test_mktdata["close"][start] - test_mktdata["close"][end])/test_mktdata["close"][start]# - COMPARE_ERROR
    pnl_config.stoploss = expected_loss
    
    pnl_config:PnlCalcConfig = get_pnl_config_stoploss(expected_stoploss=expected_loss)

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )

    #Run through the market data
    for i in range(1, len(test_mktdata)):
        action:Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.BUY if i==start else Buy_Sell_Action_Enum.HOLD
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action
        )
    #Check the result
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    assert len(trade_book_keeper_agent.archive_long_positions_list) == 1
    
    mtm = trade_book_keeper_agent.calculate_mtm()
    assert abs(mtm - -expected_loss ) < COMPARE_ERROR

    pass


@pytest.mark.skipif("tradesignal_short_with_stoploss" not in test_cases, reason="Not implemented yet")
def test_tradesignal_short_with_stoploss(get_test_ascending_mkt_data, get_pnl_config_stoploss) -> None:
    """_summary_

    Args:
        get_test_ascending_mkt_data (_type_): _description_
        get_pnl_config_stoploss (_type_): _description_
    """
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    pnl_config = PnlCalcConfig.get_default()
    start:int = int(DATA_DIM_MIN/4)
    end:int = start + int(DATA_DIM_MIN/5)
    
    expected_loss = (test_mktdata["close"][end] - test_mktdata["close"][start])/test_mktdata["close"][start]# - COMPARE_ERROR
    pnl_config.stoploss = expected_loss
    
    pnl_config:PnlCalcConfig = get_pnl_config_stoploss(expected_stoploss=expected_loss)

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )

    #Run through the market data
    for i in range(1, len(test_mktdata)):
        action:Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.SELL if i==start else Buy_Sell_Action_Enum.HOLD
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action
        )
    #Check the result
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 0
    assert len(trade_book_keeper_agent.archive_short_positions_list) == 1
    
    mtm = trade_book_keeper_agent.calculate_mtm()
    assert abs(mtm - -expected_loss ) < COMPARE_ERROR

    pass

@pytest.mark.skipif("tradesignal_long_with_short_positions" not in test_cases, reason="Not implemented yet")
def test_tradesignal_long_with_short_positions(get_test_ascending_mkt_data) -> None:
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)

    pnl_config = PnlCalcConfig.get_default()
    pnl_config.max_position_per_symbol = 10
    first_long:int = int(DATA_DIM_MIN/5)
    second_long:int = first_long + int(DATA_DIM_MIN/5)
    first_short:int = second_long + int(DATA_DIM_MIN/5)

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )
    
    #Run through the market data
    for i in range(1, len(test_mktdata)):
        if i in (first_long, second_long):
            action:Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.BUY
            logger.info(f"{action} at {i} - {test_mktdata.index[i]}")
        elif i == first_short:
            action:Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.SELL
            logger.info(f"{action} at {i} - {test_mktdata.index[i]}")
        else:
            action:Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.HOLD
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action
        )
        
    #Check the result
    
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 1
    assert len(trade_book_keeper_agent.archive_long_positions_list) == 1
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 0
    assert len(trade_book_keeper_agent.archive_short_positions_list) == 0
    
    assert trade_book_keeper_agent.archive_long_positions_list[0].entry_datetime == test_mktdata.index[first_long]
    assert trade_book_keeper_agent.outstanding_long_position_list[0].entry_datetime == test_mktdata.index[second_long]


@pytest.mark.skipif("tradesignal_short_with_long_positions" not in test_cases, reason="Not implemented yet")
def test_tradesignal_short_with_long_positions(get_test_descending_mkt_data) -> None:
    test_mktdata: pd.DataFrame = get_test_descending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)

    pnl_config = PnlCalcConfig.get_default()
    pnl_config.max_position_per_symbol = 10
    first_short:int = int(DATA_DIM_MIN/5)
    second_short:int = first_short + int(DATA_DIM_MIN/5)
    first_long:int = second_short+ int(DATA_DIM_MIN/5)

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )

    #Run through the market data
    for i in range(1, len(test_mktdata)):
        if i in (first_short, second_short):
            action:Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.SELL
            logger.info(f"{action} at {i} - {test_mktdata.index[i]}")
        elif i == first_long:
            action:Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.BUY
            logger.info(f"{action} at {i} - {test_mktdata.index[i]}")
        else:
            action:Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.HOLD
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action
        )

    #Check the result
    
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 1
    assert len(trade_book_keeper_agent.archive_short_positions_list) == 1
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    assert len(trade_book_keeper_agent.archive_long_positions_list) == 0, f"{trade_book_keeper_agent.archive_long_positions_list}"

    assert trade_book_keeper_agent.archive_short_positions_list[0].entry_datetime == test_mktdata.index[first_short]
    assert trade_book_keeper_agent.outstanding_short_position_list[0].entry_datetime == test_mktdata.index[second_short]