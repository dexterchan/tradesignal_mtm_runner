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

@pytest.fixture
def get_pnl_config_stoploss() -> PnlCalcConfig:
    def _get_pnl_config_stoploss(expected_stoploss:float) -> PnlCalcConfig:
        pnl_config: PnlCalcConfig = PnlCalcConfig.get_default()
        pnl_config.stoploss = expected_stoploss
        return pnl_config
    return _get_pnl_config_stoploss

def test_stop_loss_long(get_test_descending_mkt_data, get_pnl_config_stoploss) -> None:
    test_mktdata: pd.DataFrame = get_test_descending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    #print(test_mktdata)
    start = 5
    end = 8
    expected_loss = (test_mktdata["close"][start] - test_mktdata["close"][end])/test_mktdata["close"][start] - COMPARE_ERROR
    pnl_config:PnlCalcConfig = get_pnl_config_stoploss(expected_stoploss=expected_loss)

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )

    p = ProxyTrade(
            symbol=test_symbol,
            entry_price=test_mktdata["close"][start],
            entry_datetime=test_mktdata.index[start],
            unit=100,
            direction=LongShort_Enum.LONG,
            inventory_mode=Inventory_Mode.FIFO,
            fee_rate=0.00
        )
    #Run through the market data
    for i in range(1, len(test_mktdata)):
        if i == start:
            #Simulate buy here
            trade_book_keeper_agent.outstanding_long_position_list.append(p)
        logger.debug(f"{i}:{p.is_closed}")
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=Buy_Sell_Action_Enum.HOLD
        )
    #Check the result
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    assert len(trade_book_keeper_agent.archive_long_positions_list) == 1
    assert trade_book_keeper_agent.calculate_pnl_from_mtm_history() < expected_loss
    assert (-expected_loss - trade_book_keeper_agent.calculate_pnl_from_mtm_history()) < COMPARE_ERROR*2
    logger.debug(trade_book_keeper_agent.calculate_pnl_from_mtm_history())
    logger.debug(trade_book_keeper_agent.mtm_history)
    logger.debug(expected_loss)
    

def test_stop_loss_short(get_test_ascending_mkt_data, get_pnl_config_stoploss) -> None:
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM_MIN, step=DATA_MOVEMENT)
    #print(test_mktdata)
    start = 5
    end = 8
    expected_loss = (test_mktdata["close"][end] - test_mktdata["close"][start])/test_mktdata["close"][start] - COMPARE_ERROR
    pnl_config:PnlCalcConfig = get_pnl_config_stoploss(expected_stoploss=expected_loss)

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )

    p = ProxyTrade(
            symbol=test_symbol,
            entry_price=test_mktdata["close"][start],
            entry_datetime=test_mktdata.index[start],
            unit=100,
            direction=LongShort_Enum.SHORT,
            inventory_mode=Inventory_Mode.FIFO,
            fee_rate=0.00
        )
    #Run through the market data
    for i in range(1, len(test_mktdata)):
        if i == start:
            #Simulate buy here
            trade_book_keeper_agent.outstanding_short_position_list.append(p)
        logger.debug(f"{i}:{p.is_closed}")
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=Buy_Sell_Action_Enum.HOLD
        )
    #Check the result
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 0
    assert len(trade_book_keeper_agent.archive_short_positions_list) == 1
    assert trade_book_keeper_agent.calculate_pnl_from_mtm_history() < expected_loss
    assert (-expected_loss - trade_book_keeper_agent.calculate_pnl_from_mtm_history()) < COMPARE_ERROR*2
    logger.debug(trade_book_keeper_agent.calculate_pnl_from_mtm_history())
    logger.debug(trade_book_keeper_agent.mtm_history)
    logger.debug(expected_loss)