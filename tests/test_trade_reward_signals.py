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
COMPARE_ERROR = 0.1
from datetime import datetime, timedelta
import pytest
import logging

logger = logging.getLogger(__name__)

test_symbol = "ETHUSD"


@pytest.fixture
def get_pnl_config_stoploss() -> PnlCalcConfig:
    def _get_pnl_config_stoploss(expected_stoploss: float) -> PnlCalcConfig:
        pnl_config: PnlCalcConfig = PnlCalcConfig.get_default()
        pnl_config.stoploss = expected_stoploss
        return pnl_config

    return _get_pnl_config_stoploss


test_cases: list = [
    "tradesignal_long_no_roi_no_stoploss",
    "tradesignal_short_no_roi_no_stoploss",
    "tradesignal_long_with_roi",
    "tradesignal_short_with_roi",
    "tradesignal_long_with_stoploss",
    "tradesignal_short_with_stoploss",
    "tradesignal_long_with_short_positions",
    "tradesignal_short_with_long_positions",
]


@pytest.mark.skipif(
    "tradesignal_long_no_roi_no_stoploss" not in test_cases,
    reason="Not implemented yet",
)
def test_tradesignal_long_no_roi_no_stoploss(get_test_ascending_mkt_data) -> None:
    """simple testing of long signal with no stoploss and no roi

    Args:
        get_test_ascending_mkt_data (_type_): _description_
    """
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(
        dim=DATA_DIM_MIN, step=DATA_MOVEMENT
    )
    # print(test_mktdata)
    start = 5

    pnl_config: PnlCalcConfig = PnlCalcConfig.get_default()

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )
    # Run through the market data
    for i in range(len(test_mktdata)):
        action: Buy_Sell_Action_Enum = (
            Buy_Sell_Action_Enum.BUY if i == start else Buy_Sell_Action_Enum.HOLD
        )
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action,
        )

    # Check the result
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 1
    assert len(trade_book_keeper_agent.archive_long_positions_list) == 0

    accumulated_pnl: float = 0
    for trade in trade_book_keeper_agent.outstanding_long_position_list:
        accumulated_pnl += trade.calculate_pnl_normalized(test_mktdata["close"][-1])
    agent_mtm: float = trade_book_keeper_agent.calculate_pnl_from_mtm_history()
    assert abs(accumulated_pnl - agent_mtm) < COMPARE_ERROR


@pytest.mark.skipif(
    "tradesignal_short_no_roi_no_stoploss" not in test_cases,
    reason="Not implemented yet",
)
def test_tradesignal_short_no_roi_no_stoploss(
    get_test_descending_mkt_data, get_test_pnl_calc_config
) -> None:
    """_summary_

    Args:
        get_test_descending_mkt_data (_type_): _description_
    """
    test_mktdata: pd.DataFrame = get_test_descending_mkt_data(
        dim=DATA_DIM_MIN, step=DATA_MOVEMENT
    )
    # print(test_mktdata)
    start = 5

    pnl_config: PnlCalcConfig = get_test_pnl_calc_config(enable_short_position=True)

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )
    # Run through the market data
    for i in range(len(test_mktdata)):
        action: Buy_Sell_Action_Enum = (
            Buy_Sell_Action_Enum.SELL if i == start else Buy_Sell_Action_Enum.HOLD
        )
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action,
        )

    # Check the result
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 1
    assert len(trade_book_keeper_agent.archive_short_positions_list) == 0

    accumulated_pnl: float = 0
    for trade in trade_book_keeper_agent.outstanding_short_position_list:
        accumulated_pnl += trade.calculate_pnl_normalized(test_mktdata["close"][-1])
    agent_mtm: float = trade_book_keeper_agent.calculate_pnl_from_mtm_history()
    assert abs(accumulated_pnl - agent_mtm) < COMPARE_ERROR


@pytest.mark.skipif(
    "tradesignal_long_with_roi" not in test_cases, reason="Not implemented yet"
)
def test_tradesignal_long_with_roi(
    get_test_ascending_mkt_data, get_test_pnl_calc_config
) -> None:
    """simple testing of long signal with roi

    Args:
        get_test_ascending_mkt_data (_type_): _description_
    """
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(
        dim=DATA_DIM_MIN, step=DATA_MOVEMENT
    )
    close_price: pd.Series = test_mktdata["close"]

    pnl_config = get_test_pnl_calc_config()
    start_trade_inx: int = int(DATA_DIM_MIN / 4)

    end_trade_inx: int = int(DATA_DIM_MIN / 5) + start_trade_inx
    # ((pnl_length) * DATA_MOVEMENT)

    expect_mtm: float = (
        close_price[end_trade_inx] - close_price[start_trade_inx]
    ) / close_price[start_trade_inx]

    pnl_config.roi = {end_trade_inx: expect_mtm}

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )

    # Run through the market data
    for i in range(len(test_mktdata)):
        action: Buy_Sell_Action_Enum = (
            Buy_Sell_Action_Enum.BUY
            if i == start_trade_inx
            else Buy_Sell_Action_Enum.HOLD
        )
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action,
        )
        if len(trade_book_keeper_agent.outstanding_long_position_list) > 0:
            trade = trade_book_keeper_agent.outstanding_long_position_list[0]
            logger.debug(
                f"{i} : {trade.is_closed} : {trade_book_keeper_agent.mtm_history[-1]} : {trade.calculate_pnl_normalized(test_mktdata['close'][i])} "
            )
    # Check the result
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    assert len(trade_book_keeper_agent.archive_long_positions_list) == 1
    logger.debug(trade_book_keeper_agent.mtm_history)
    logger.debug(pnl_config.roi)
    mtm = trade_book_keeper_agent.calculate_pnl_from_mtm_history()
    assert (
        abs(mtm - expect_mtm) < COMPARE_ERROR
    ), f"mtm {mtm} != expected_mtm{expect_mtm}"
    assert len(test_mktdata) == len(trade_book_keeper_agent.mtm_history)
    pass


@pytest.mark.skipif(
    "tradesignal_short_with_roi" not in test_cases, reason="Not implemented yet"
)
def test_tradesignal_short_with_roi(
    get_test_descending_mkt_data, get_test_pnl_calc_config
) -> None:
    """simple testing of short signal with roi

    Args:
        get_test_descending_mkt_data (_type_): _description_
    """
    test_mktdata: pd.DataFrame = get_test_descending_mkt_data(
        dim=DATA_DIM_MIN, step=DATA_MOVEMENT
    )
    close_price: pd.Series = test_mktdata["close"]
    pnl_config = get_test_pnl_calc_config(enable_short_position=True)
    start_trade_inx: int = int(DATA_DIM_MIN / 4)
    end_trade_inx: int = int(DATA_DIM_MIN / 5) + start_trade_inx

    expect_mtm: float = (
        close_price[start_trade_inx] - close_price[end_trade_inx]
    ) / close_price[start_trade_inx]

    pnl_config.roi = {
        end_trade_inx: expect_mtm,
    }

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )

    # Run through the market data
    for i in range(len(test_mktdata)):
        action: Buy_Sell_Action_Enum = (
            Buy_Sell_Action_Enum.SELL
            if i == start_trade_inx
            else Buy_Sell_Action_Enum.HOLD
        )
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action,
        )
    # Check the result
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 0
    assert len(trade_book_keeper_agent.archive_short_positions_list) == 1
    # logger.info(trade_book_keeper_agent.mtm_history)
    # logger.info(pnl_config.roi)
    mtm = trade_book_keeper_agent.calculate_pnl_from_mtm_history()
    assert abs(mtm - expect_mtm) < COMPARE_ERROR

    pass


@pytest.mark.skipif(
    "tradesignal_long_with_stoploss" not in test_cases, reason="Not implemented yet"
)
def test_tradesignal_long_with_stoploss(
    get_test_descending_mkt_data, get_pnl_config_stoploss
) -> None:
    """simple testing of long signal with stoploss

    Args:
        get_test_descending_mkt_data (_type_): _description_
    """
    test_mktdata: pd.DataFrame = get_test_descending_mkt_data(
        dim=DATA_DIM_MIN, step=DATA_MOVEMENT
    )
    pnl_config = PnlCalcConfig.get_default()
    start: int = int(DATA_DIM_MIN / 4)
    end: int = start + int(DATA_DIM_MIN / 5)

    expected_loss = (
        test_mktdata["close"][start] - test_mktdata["close"][end]
    ) / test_mktdata["close"][
        start
    ]  # - COMPARE_ERROR
    pnl_config.stoploss = expected_loss

    pnl_config: PnlCalcConfig = get_pnl_config_stoploss(expected_stoploss=expected_loss)

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )

    # Run through the market data
    for i in range(len(test_mktdata)):
        action: Buy_Sell_Action_Enum = (
            Buy_Sell_Action_Enum.BUY if i == start else Buy_Sell_Action_Enum.HOLD
        )
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action,
        )
    # Check the result
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    assert len(trade_book_keeper_agent.archive_long_positions_list) == 1

    mtm = trade_book_keeper_agent.calculate_pnl_from_mtm_history()
    assert abs(mtm - -expected_loss) < COMPARE_ERROR

    pass


@pytest.mark.skipif(
    "tradesignal_short_with_stoploss" not in test_cases, reason="Not implemented yet"
)
def test_tradesignal_short_with_stoploss(
    get_test_ascending_mkt_data,
    get_pnl_config_stoploss,
) -> None:
    """_summary_

    Args:
        get_test_ascending_mkt_data (_type_): _description_
        get_pnl_config_stoploss (_type_): _description_
    """
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(
        dim=DATA_DIM_MIN, step=DATA_MOVEMENT
    )

    start: int = int(DATA_DIM_MIN / 4)
    end: int = start + int(DATA_DIM_MIN / 5)

    expected_loss = (
        test_mktdata["close"][end] - test_mktdata["close"][start]
    ) / test_mktdata["close"][
        start
    ]  # - COMPARE_ERROR

    pnl_config: PnlCalcConfig = get_pnl_config_stoploss(expected_stoploss=expected_loss)
    pnl_config.enable_short_position = True
    pnl_config.stoploss = expected_loss

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )

    # Run through the market data
    for i in range(len(test_mktdata)):
        action: Buy_Sell_Action_Enum = (
            Buy_Sell_Action_Enum.SELL if i == start else Buy_Sell_Action_Enum.HOLD
        )
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action,
        )
    # Check the result
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 0
    assert len(trade_book_keeper_agent.archive_short_positions_list) == 1

    mtm = trade_book_keeper_agent.calculate_pnl_from_mtm_history()
    assert abs(mtm - -expected_loss) < COMPARE_ERROR

    pass


@pytest.mark.skipif(
    "tradesignal_long_with_short_positions" not in test_cases,
    reason="Not implemented yet",
)
def test_tradesignal_long_with_short_positions(get_test_ascending_mkt_data) -> None:
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(
        dim=DATA_DIM_MIN, step=DATA_MOVEMENT
    )

    pnl_config = PnlCalcConfig.get_default()
    pnl_config.max_position_per_symbol = 10
    first_long: int = int(DATA_DIM_MIN / 5)
    second_long: int = first_long + int(DATA_DIM_MIN / 5)
    first_short: int = second_long + int(DATA_DIM_MIN / 5)

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )

    expected_pnl_1 = (
        test_mktdata["close"][first_short] - test_mktdata["close"][first_long]
    ) / test_mktdata["close"][first_long]
    expected_pnl_2 = (
        test_mktdata["close"][-1] - test_mktdata["close"][second_long]
    ) / test_mktdata["close"][second_long]

    # Run through the market data
    for i in range(len(test_mktdata)):
        if i in (first_long, second_long):
            action: Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.BUY
            logger.info(f"{action} at {i} - {test_mktdata.index[i]}")
        elif i == first_short:
            action: Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.SELL
            logger.info(f"{action} at {i} - {test_mktdata.index[i]}")
        else:
            action: Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.HOLD
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action,
        )

    # Check the result

    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 1
    assert len(trade_book_keeper_agent.archive_long_positions_list) == 1
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 0
    assert len(trade_book_keeper_agent.archive_short_positions_list) == 0

    trade1 = trade_book_keeper_agent.archive_long_positions_list[0]
    trade2 = trade_book_keeper_agent.outstanding_long_position_list[0]
    assert trade1.entry_datetime == test_mktdata.index[first_long]
    assert trade2.entry_datetime == test_mktdata.index[second_long]
    assert trade1.exit_datetime == test_mktdata.index[first_short]

    # Check the mtm
    pnl_1 = trade1.calculate_pnl_normalized(price=trade1.exit_price)
    pnl_2 = trade2.calculate_pnl_normalized(price=test_mktdata["close"][-1])
    assert expected_pnl_1 == pnl_1
    assert expected_pnl_2 == pnl_2

    total_pnl_expected = pnl_1 + pnl_2
    total_pnl = trade_book_keeper_agent.calculate_pnl_from_mtm_history()
    assert abs(total_pnl_expected - total_pnl) < COMPARE_ERROR

    _pnl: float = trade_book_keeper_agent.calculate_pnl_from_mtm_history()
    _sharpe_ratio: float = trade_book_keeper_agent._calculate_sharpe_ratio()
    logger.debug(f"Pnl: {_pnl} Sharpe Ratio: {_sharpe_ratio}")


@pytest.mark.skipif(
    "tradesignal_short_with_long_positions" not in test_cases,
    reason="Not implemented yet",
)
def test_tradesignal_short_with_long_positions(
    get_test_descending_mkt_data, get_test_pnl_calc_config
) -> None:
    test_mktdata: pd.DataFrame = get_test_descending_mkt_data(
        dim=DATA_DIM_MIN, step=DATA_MOVEMENT
    )

    pnl_config = get_test_pnl_calc_config(enable_short_position=True)
    pnl_config.max_position_per_symbol = 10
    first_short: int = int(DATA_DIM_MIN / 5)
    second_short: int = first_short + int(DATA_DIM_MIN / 5)
    first_long: int = second_short + int(DATA_DIM_MIN / 5)

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )

    expected_pnl_1 = (
        test_mktdata["close"][first_short] - test_mktdata["close"][first_long]
    ) / test_mktdata["close"][first_short]
    expected_pnl_2 = (
        test_mktdata["close"][second_short] - test_mktdata["close"][-1]
    ) / test_mktdata["close"][second_short]

    # Run through the market data
    for i in range(len(test_mktdata)):
        if i in (first_short, second_short):
            action: Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.SELL
            logger.info(f"{action} at {i} - {test_mktdata.index[i]}")
        elif i == first_long:
            action: Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.BUY
            logger.info(f"{action} at {i} - {test_mktdata.index[i]}")
        else:
            action: Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.HOLD
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action,
        )

    # Check the result

    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 1
    assert len(trade_book_keeper_agent.archive_short_positions_list) == 1
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    assert (
        len(trade_book_keeper_agent.archive_long_positions_list) == 0
    ), f"{trade_book_keeper_agent.archive_long_positions_list}"

    first_trade = trade_book_keeper_agent.archive_short_positions_list[0]
    second_trade = trade_book_keeper_agent.outstanding_short_position_list[0]

    assert first_trade.entry_datetime == test_mktdata.index[first_short]
    assert first_trade.exit_datetime == test_mktdata.index[first_long]
    assert second_trade.entry_datetime == test_mktdata.index[second_short]

    pnl_first = first_trade.calculate_pnl_normalized(price=first_trade.exit_price)
    pnl_second = second_trade.calculate_pnl_normalized(price=test_mktdata["close"][-1])

    assert abs(pnl_second - expected_pnl_2) < COMPARE_ERROR
    assert abs(pnl_first - expected_pnl_1) < COMPARE_ERROR

    total_pnl_expected = pnl_first + pnl_second
    total_pnl = trade_book_keeper_agent.calculate_pnl_from_mtm_history()
    logger.debug(f"first trade start:{first_short} ")
    logger.debug(f"second trade start:{second_short} ")
    logger.debug(f"first trade end:{first_long} ")
    logger.debug(f"first trade pnl:{pnl_first} : {first_trade}")
    logger.debug(f"second trade pnl:{pnl_second} : {second_trade} ")

    logger.debug(trade_book_keeper_agent.mtm_history)
    assert abs(total_pnl - total_pnl_expected) < COMPARE_ERROR


@pytest.mark.skipif(
    "tradesignal_short_with_long_positions" not in test_cases,
    reason="Not implemented yet",
)
def test_tradesignal_flat_mkt_data_with_disable_short_positions(
    get_test_flat_mkt_data, get_test_pnl_calc_config
) -> None:
    test_mktdata: pd.DataFrame = get_test_flat_mkt_data(dim=DATA_DIM_MIN)

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=get_test_pnl_calc_config(enable_short_position=False),
        symbol=test_symbol,
    )
    first_short: int = int(DATA_DIM_MIN / 5)

    # Run through the market data
    for i in range(len(test_mktdata)):
        action = (
            Buy_Sell_Action_Enum.SELL if i == first_short else Buy_Sell_Action_Enum.HOLD
        )
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action,
        )

    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 0
    assert len(trade_book_keeper_agent.archive_short_positions_list) == 0
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    assert len(trade_book_keeper_agent.archive_long_positions_list) == 0


def test_tradesignal_ascending_mkt_data_with_long_positions(
    get_test_ascending_mkt_data, get_test_pnl_calc_config
) -> None:
    test_mktdata: pd.DataFrame = get_test_ascending_mkt_data(dim=DATA_DIM_MIN)
    test_fee_rate: float = 0.1
    pnl_config: PnlCalcConfig = get_test_pnl_calc_config(
        enable_short_position=True, fee_rate=test_fee_rate
    )
    pnl_config.max_position_per_symbol = 10
    first_long: int = int(DATA_DIM_MIN / 5)
    first_short: int = first_long + int(DATA_DIM_MIN / 5)
    second_long: int = first_short + int(DATA_DIM_MIN / 5)

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config, symbol=test_symbol
    )

    expected_pnl_1 = (
        test_mktdata["close"][first_short] - test_mktdata["close"][first_long]
    ) / test_mktdata["close"][first_long] - test_fee_rate * 2
    expected_pnl_2 = (
        test_mktdata["close"][-1] - test_mktdata["close"][second_long]
    ) / test_mktdata["close"][second_long] - test_fee_rate

    # Run through the market data
    action: Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.HOLD
    for i in range(len(test_mktdata)):
        if i in (first_long, second_long):
            action = Buy_Sell_Action_Enum.BUY
        elif i in (first_short,):
            action = Buy_Sell_Action_Enum.SELL
        else:
            action = Buy_Sell_Action_Enum.HOLD

        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action,
        )

    # Check the result
    # 1) Check position
    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 0
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 1
    assert len(trade_book_keeper_agent.archive_short_positions_list) == 0
    assert len(trade_book_keeper_agent.archive_long_positions_list) == 1

    # 2) check trades
    first_trade = trade_book_keeper_agent.archive_long_positions_list[0]
    second_trade = trade_book_keeper_agent.outstanding_long_position_list[0]

    assert first_trade.entry_datetime == test_mktdata.index[first_long]
    assert first_trade.exit_datetime == test_mktdata.index[first_short]
    assert second_trade.entry_datetime == test_mktdata.index[second_long]

    # 3) check pnl
    pnl_first: float = first_trade.calculate_pnl_normalized(
        price=first_trade.exit_price, fee_included=True
    )
    pnl_second: float = second_trade.calculate_pnl_normalized(
        price=test_mktdata["close"][-1], fee_included=True
    )

    assert (
        abs(pnl_first - expected_pnl_1) < COMPARE_ERROR
    ), f"pnl_first:{pnl_first}, expected_pnl_1:{expected_pnl_1}"

    assert (
        abs(pnl_second - expected_pnl_2) < COMPARE_ERROR
    ), f"{second_trade}, last mkt price: {test_mktdata['close'][-1]}, pnl_second:{pnl_second}, expected_pnl_2:{expected_pnl_2}"

    # 4) check trade book history
    total_pnl = trade_book_keeper_agent.calculate_pnl_from_mtm_history()
    assert (
        abs(total_pnl - (pnl_first + pnl_second)) < COMPARE_ERROR
    ), f"total_pnl:{total_pnl}, pnl_first:{pnl_first}, pnl_second:{pnl_second}"
    pass


def test_tradesignal_flat_mkt_data_with_short_position_plus_fee(
    get_test_flat_mkt_data, get_test_pnl_calc_config
) -> None:
    test_mktdata: pd.DataFrame = get_test_flat_mkt_data(dim=DATA_DIM_MIN)
    test_fee_rate: float = 0.1
    pnl_config: PnlCalcConfig = get_test_pnl_calc_config(
        enable_short_position=True, fee_rate=test_fee_rate
    )
    pnl_config.max_position_per_symbol = 10
    first_short: int = int(DATA_DIM_MIN / 5)
    second_short: int = first_short + int(DATA_DIM_MIN / 5)
    first_long: int = second_short + int(DATA_DIM_MIN / 5)

    trade_book_keeper_agent: TradeBookKeeperAgent = TradeBookKeeperAgent(
        pnl_config=pnl_config,
        symbol=test_symbol,
    )

    expected_pnl_1 = (
        test_mktdata["close"][first_short] - test_mktdata["close"][first_long]
    ) / test_mktdata["close"][first_short] - test_fee_rate * 2
    expected_pnl_2 = (
        test_mktdata["close"][second_short] - test_mktdata["close"][-1]
    ) / test_mktdata["close"][second_short] - test_fee_rate

    # Run through the market data
    for i in range(len(test_mktdata)):
        if i in (first_short, second_short):
            action: Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.SELL
            logger.info(f"{action} at {i} - {test_mktdata.index[i]}")
        elif i == first_long:
            action: Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.BUY
            logger.info(f"{action} at {i} - {test_mktdata.index[i]}")
        else:
            action: Buy_Sell_Action_Enum = Buy_Sell_Action_Enum.HOLD
        trade_book_keeper_agent.run_at_timestamp(
            dt=test_mktdata.index[i],
            price=test_mktdata["close"][i],
            price_diff=test_mktdata["price_movement"][i],
            buy_sell_action=action,
        )

    # Check the result

    assert len(trade_book_keeper_agent.outstanding_short_position_list) == 1
    assert len(trade_book_keeper_agent.archive_short_positions_list) == 1
    assert len(trade_book_keeper_agent.outstanding_long_position_list) == 0
    assert (
        len(trade_book_keeper_agent.archive_long_positions_list) == 0
    ), f"{trade_book_keeper_agent.archive_long_positions_list}"

    first_trade = trade_book_keeper_agent.archive_short_positions_list[0]
    second_trade = trade_book_keeper_agent.outstanding_short_position_list[0]

    assert first_trade.entry_datetime == test_mktdata.index[first_short]
    assert first_trade.exit_datetime == test_mktdata.index[first_long]
    assert second_trade.entry_datetime == test_mktdata.index[second_short]

    pnl_first: float = first_trade.calculate_pnl_normalized(
        price=first_trade.exit_price, fee_included=True
    )
    pnl_second: float = second_trade.calculate_pnl_normalized(
        price=test_mktdata["close"][-1], fee_included=True
    )

    assert (
        abs(pnl_first - expected_pnl_1) < COMPARE_ERROR
    ), f"pnl_first:{pnl_first}, expected_pnl_1:{expected_pnl_1}"

    assert (
        abs(pnl_second - expected_pnl_2) < COMPARE_ERROR
    ), f"pnl_second:{pnl_second}, expected_pnl_2:{expected_pnl_2}"

    total_pnl_expected = pnl_first + pnl_second
    total_pnl = trade_book_keeper_agent.calculate_pnl_from_mtm_history()
    logger.debug(f"first trade start:{first_short} ")
    logger.debug(f"second trade start:{second_short} ")
    logger.debug(f"first trade end:{first_long} ")
    logger.debug(f"first trade pnl:{pnl_first} : {first_trade}")
    logger.debug(f"second trade pnl:{pnl_second} : {second_trade} ")

    logger.debug(trade_book_keeper_agent.mtm_history)
    assert (
        abs(total_pnl - total_pnl_expected) < COMPARE_ERROR
    ), f"total_pnl:{total_pnl}, total_pnl_expected {total_pnl_expected}"
