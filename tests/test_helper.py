from datetime import datetime, timedelta
from tradesignal_mtm_runner.helper import ROI_Helper

def test_roi_helper() -> None:
    roi_helper: ROI_Helper = ROI_Helper(roi_dict={40: 0.0, 30: 0.01, 20: 0.02, 0: 0.04})
    e_date = datetime.utcnow()
    price_list = roi_helper.get_all_take_profit_pnl(
        entry_date=e_date, current_date=e_date + timedelta(minutes=31)
    )
    assert price_list == [0.04, 0.02, 0.01]
    price_list = roi_helper.get_all_take_profit_pnl(
        entry_date=e_date, current_date=e_date + timedelta(minutes=40)
    )
    assert price_list == [0.04, 0.02, 0.01, 0]

    price_list = roi_helper.get_all_take_profit_pnl(
        entry_date=e_date, current_date=e_date
    )
    assert price_list == [0.04]

    assert roi_helper.can_take_profit(
        entry_date=e_date,
        current_date=e_date + timedelta(minutes=22),
        normalized_pnl=0.05,
    ), "should be able to take profit"

    assert roi_helper.can_take_profit(
        entry_date=e_date,
        current_date=e_date + timedelta(minutes=32),
        normalized_pnl=0.015,
    ), "should be able to take profit"

    assert not roi_helper.can_take_profit(
        entry_date=e_date,
        current_date=e_date + timedelta(minutes=60),
        normalized_pnl=-0.9,
    ), "should be able to take profit"

    assert not roi_helper.can_take_profit(
        entry_date=e_date,
        current_date=e_date + timedelta(minutes=10),
        normalized_pnl=0.03,
    ), "should be able to take profit"

    assert roi_helper.can_take_profit(
        entry_date=e_date,
        current_date=e_date + timedelta(minutes=21),
        normalized_pnl=0.03,
    ), "should be able to take profit"
