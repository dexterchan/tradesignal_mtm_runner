import numpy as np
from datetime import datetime
from .data_struct import IndexedList
import logging

logger = logging.getLogger(__name__)

class ROI_Helper:
    def __init__(self, roi_dict: dict[int, float]) -> None:
        self._roi_dict = {k * 60: v for k, v in roi_dict.items()}
        _roi_seconds_list = [k for k in self._roi_dict.keys()]
        self._roi_seconds_list: list[int] = sorted(_roi_seconds_list)
        self.indexed_list = IndexedList(base_list=self._roi_seconds_list)
        pass

    def get_all_take_profit_pnl(
        self, entry_date: datetime, current_date: datetime
    ) -> list[float]:
        """ Search all ROI values < current_date - entry_date
            calculate cost is O(NlogR)
        Args:
            entry_date (datetime): entry datetime
            current_date (datetime): current datetime

        Returns:
            List[float]: List of price to take profit
        """
        time_diff_seconds = int((current_date - entry_date).total_seconds())

        roi_take_profit_prices: list[float] = [
            self._roi_dict[k]
            for k in self.indexed_list.search_value_left(value=time_diff_seconds)
        ]

        return roi_take_profit_prices

    def can_take_profit(
        self, entry_date: datetime, current_date: datetime, normalized_pnl: float
    ) -> bool:
        """determine if we can take profit according to minimum roi logic

        Args:
            entry_date (datetime): entry datetime
            current_date (datetime): current datetime
            normalized_pnl (float): normalized_pnl = cur_price/entry_price


        Returns:
            bool: _description_
        """
        roi_pnls: np.array = np.array(
            self.get_all_take_profit_pnl(
                entry_date=entry_date,
                current_date=current_date,
            )
        )
        _chk = normalized_pnl - roi_pnls
        logger.debug(_chk)
        if len(_chk) == 0:
            return False
        else:
            if _chk.max() > 0:
                logger.debug(f"ROI helper should close positon pnl:{normalized_pnl} > roi_pnl{roi_pnls} with diff {_chk}")
                return True
            else:
                logger.debug(f"ROI helper ignore pnl:{normalized_pnl} > roi_pnl{roi_pnls} with diff {_chk}")
                return False

