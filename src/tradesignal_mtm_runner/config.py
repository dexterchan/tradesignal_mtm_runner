from __future__ import annotations
from pydantic import BaseModel, Field, validator


class PnlCalcConfig(BaseModel):
    """_summary_
        roi - Return On Investment (ROI):
        e.g. roi = {
            40: 0.0,
            30: 0.01,
            20: 0.02,
            0: 0.04
        }
        - Sell whenever 4% profit was reached
        - Sell when 2% profit was reached (in effect after 20 minutes)
        - Sell when 1% profit was reached (in effect after 30 minutes)
        - Sell when trade is non-loosing (in effect after 40 minutes)

        stoploss - profit ratio to stop loss
        fixed_stake_unit_amount - notional of each trade
        enable_short_position - enable short position
        max_position_per_symbol - number of open position per symbol
        fee_rate - fee rate of each trade
        laid_back_tax - tax rate of not holding any positions at time t

    Args:
        BaseModel (_type_): _description_

    Returns:
        _type_: _description_
    """

    roi: dict[int, float] = Field(default_factory=dict)
    stoploss: float = float("-inf")
    fixed_stake_unit_amount: float = 100
    enable_short_position: bool = False
    max_position_per_symbol: int = 1
    fee_rate: float = 0
    laid_back_tax: float = 0.0001

    @classmethod
    def get_default(cls) -> PnlCalcConfig:
        return cls(roi={"0": float("inf")}, stoploss=float("-inf"), laid_back_tax=0)

    @validator("max_position_per_symbol")
    def max_position_per_symbol_validation(cls, v):
        assert isinstance(v, int)
        assert v > 0
        return v

    @validator("fixed_stake_unit_amount")
    def fixed_stake_unit_amount_validation(cls, v):
        assert isinstance(v, float)
        assert v > 0, "fixed unit amount should be > 0"
        return v

    @validator("stoploss")
    def stopless_validation(cls, v):
        assert v < 0, "must be less than 0 or greater than -1"
        return v

    @validator("roi")
    def roi_validation(cls, d):
        assert isinstance(d, dict), "roi should be Dict"
        assert len(d) > 0
        new_values = {}
        for k, v in d.items():
            assert isinstance(int(k), int), "roi key should be convertable to int"
            assert isinstance(v, float)
            assert int(k) >= 0, "roi key should be positive or zero"
            assert v >= 0, "roi value should be larger than 0"
            new_values[int(k)] = v
        assert 0 in new_values, "missing default roi"
        return new_values
