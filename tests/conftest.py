import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tradesignal_mtm_runner.config import PnlCalcConfig


@pytest.fixture
def get_test_ascending_mkt_data() -> pd.DataFrame:
    def _get_data(dim: int = 10, step: int = 100):
        # Generate pandas dataframe of timestamps records
        df = pd.DataFrame(
            data={
                "timestamp": pd.date_range(
                    start=datetime.now(), periods=dim, freq=timedelta(hours=1)
                ),
                "inx": np.arange(dim),
            }
        )

        # n = datetime.now()
        # inx = [i for i in range(dim)]
        # time_stamp = [n + timedelta(minutes=i) for i in range(dim)]
        # data = [time_stamp, inx]
        # n_data = np.asarray(data)
        # df = pd.DataFrame(data=n_data.transpose(), columns=["timestamp", "inx"])
        df.set_index("timestamp", inplace=True, drop=True)
        df["close"] = df["inx"] * step + 1000

        df["price_movement"] = df["close"].diff()
        return df
        pass

    return _get_data


@pytest.fixture
def get_test_descending_mkt_data() -> pd.DataFrame:
    def _get_data(dim: int = 10, step: int = 100):
        # n = datetime.now()
        # inx = [i for i in range(dim)]
        # timestamp = [n + timedelta(minutes=i) for i in range(dim)]
        # data = [timestamp, inx]
        # n_data = np.asarray(data)
        # df = pd.DataFrame(data=n_data.transpose(), columns=["timestamp", "inx"])
        df = pd.DataFrame(
            data={
                "timestamp": pd.date_range(
                    start=datetime.now(), periods=dim, freq=timedelta(hours=1)
                ),
                "inx": np.arange(dim),
            }
        )
        df.set_index("timestamp", inplace=True, drop=True)
        max_inx = df["inx"].max()
        df["close"] = (max_inx - df["inx"]) * step + 1000
        df["price_movement"] = df["close"].diff()

        return df

    return _get_data


@pytest.fixture
def get_test_flat_mkt_data() -> pd.DataFrame:
    def _get_data(dim: int = 10, step: int = 100):
        df = pd.DataFrame(
            data={
                "timestamp": pd.date_range(
                    start=datetime.now(), periods=dim, freq=timedelta(hours=1)
                ),
                "inx": np.arange(dim),
            }
        )
        df.set_index("timestamp", inplace=True, drop=True)
        df["close"] = 1000
        df["price_movement"] = df["close"].diff()

        return df

    return _get_data


@pytest.fixture
def get_test_pnl_calc_config() -> PnlCalcConfig:
    def _get_config(
        enable_short_position: bool = True, fee_rate: float = 0
    ) -> PnlCalcConfig:
        pnl_calc_config: PnlCalcConfig = PnlCalcConfig.get_default()
        pnl_calc_config.enable_short_position = enable_short_position
        pnl_calc_config.fee_rate = fee_rate

        return pnl_calc_config

    return _get_config


# @pytest.fixture
# # Generate a PnlCalcConfig with fee=0.1
# def get_test_pnl_calc_config() -> PnlCalcConfig:
#     pnl_calc_config: PnlCalcConfig = PnlCalcConfig.get_default()
#     pnl_calc_config.fee_rate = 0.1

#     return pnl_calc_config
