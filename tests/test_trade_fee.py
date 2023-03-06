from tradesignal_mtm_runner.runner_mtm import Trade_Mtm_Runner
from tradesignal_mtm_runner.config import PnlCalcConfig
from tradesignal_mtm_runner.interfaces import ITradeSignalRunner
from tradesignal_mtm_runner.trade_reward import TradeBookKeeperAgent
from tradesignal_mtm_runner.config import PnlCalcConfig
from tradesignal_mtm_runner.models import Buy_Sell_Action_Enum, ProxyTrade, LongShort_Enum, Inventory_Mode, Proxy_Trade_Actions


import numpy as np
import pandas as pd
import pytest
from functools import reduce

test_exchange = "kraken"
test_symbol = "ETHUSD"
test_cases: list = [
    "flat",
    "flat_close",
    "ascending"
]

DATA_DIM = 10
DATA_MOVEMENT = 100
COMPARE_ERROR = 0.1
FEE_RATE = 0.1

import logging
logger = logging.getLogger(__name__)


@pytest.fixture
def get_pnl_config()-> PnlCalcConfig:
    pnl_config: PnlCalcConfig = PnlCalcConfig.get_default()
    pnl_config.fee_rate = FEE_RATE
    return pnl_config
    


@pytest.mark.skipif("flat" not in test_cases, reason="skipped")
def test_trade_pnl_runner_with_flat_data_noclose(get_test_flat_mkt_data, get_pnl_config) -> None:
    test_mktdata: pd.DataFrame = get_test_flat_mkt_data(dim=DATA_DIM, step=DATA_MOVEMENT)
    pnl_config:PnlCalcConfig = get_pnl_config
    start = 2
    
    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )

    #Run through the market data
    for i in range( len(test_mktdata)):
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
    agent_mtm:float = trade_book_keeper_agent.calculate_pnl_from_mtm_history()
    assert (agent_mtm == -FEE_RATE)
    assert trade_book_keeper_agent.outstanding_long_position_list[0].calculate_pnl_normalized(test_mktdata["close"][0], True) == agent_mtm

    pass

@pytest.mark.skipif("flat_close" not in test_cases, reason="skipped")
def test_trade_pnl_runner_with_flat_data_close(get_test_flat_mkt_data, get_pnl_config) -> None:
    test_mktdata:pd.DataFrame = get_test_flat_mkt_data(dim=DATA_DIM, step=DATA_MOVEMENT)
    pnl_config:PnlCalcConfig = get_pnl_config
    start = int(DATA_DIM * 0.2)
    close = int(DATA_DIM * 0.8)

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )
    #Run through the market data
    for i in range( len(test_mktdata)):
        action:Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.HOLD
        if i == start:
            action = Buy_Sell_Action_Enum.BUY
        elif i == close:
            action = Buy_Sell_Action_Enum.SELL
        
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action
        )
    
    #Check the result
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    assert len(trade_book_keeper_agent.archive_long_positions_list) == 1

    trade:ProxyTrade = trade_book_keeper_agent.archive_long_positions_list[0]
    agent_mtm:float = trade_book_keeper_agent.calculate_pnl_from_mtm_history()
    assert (agent_mtm == -FEE_RATE * 2)
    assert (reduce ( lambda x,y:x+y,trade_book_keeper_agent.mtm_history  )== -FEE_RATE * 2)
    assert (agent_mtm == trade.pnl_normalized)

@pytest.mark.skipif("ascending" not in test_cases, reason="skipped")
def test_trade_pnl_runner_with_ascending_data_close(get_test_ascending_mkt_data, get_pnl_config) -> None:
    test_mktdata:pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM, step=DATA_MOVEMENT)
    pnl_config:PnlCalcConfig = get_pnl_config
    start = int(DATA_DIM * 0.2)
    inx = int(DATA_DIM * 0.5)
    pnl_config.roi = {
        #inx: ((test_mktdata["close"][inx-1])/test_mktdata["close"][0] -1 ) 
        inx: ((inx)*DATA_MOVEMENT-1)/test_mktdata["close"][0]
    }
    logger.info(pnl_config.roi)
    logger.info(test_mktdata)
    

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )
    #Run through the market data
    for i in range( len(test_mktdata)):
        action:Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.HOLD
        if i == start:
            action = Buy_Sell_Action_Enum.BUY
        
        
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action
        )
    
    #Check the result
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    assert len(trade_book_keeper_agent.archive_long_positions_list) == 1

    trade:ProxyTrade = trade_book_keeper_agent.archive_long_positions_list[0]
    agent_mtm:float = trade_book_keeper_agent.calculate_pnl_from_mtm_history()
    expected_pnl = (test_mktdata["close"][inx] / test_mktdata["close"][0]) -1 - 2*FEE_RATE
    assert abs(expected_pnl - agent_mtm) < 0.001
    
    assert abs(reduce ( lambda x,y:x+y,trade_book_keeper_agent.mtm_history  ) -  expected_pnl) < 0.001
    print(trade)
    print(trade.pnl_normalized)
    print(expected_pnl)
    #assert abs( expected_pnl - trade.pnl_normalized) < 0.001
    



