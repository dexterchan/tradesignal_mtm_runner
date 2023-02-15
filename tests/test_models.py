
import pytest
from tradesignal_mtm_runner.models import Mtm_Result

@pytest.fixture()
def get_pnlresult_samples() -> list[Mtm_Result]:
    SAMPLE_FILE = "samples/sample_pnlresult.jsonl"
    pnlresults: list = []
    with open(SAMPLE_FILE, "r") as f:
        while line := f.readline():
            pnlresult = Mtm_Result.parse_raw(line)
            pnlresults.append(pnlresult)
    return pnlresults

def test_mtm_result(get_pnlresult_samples: list[Mtm_Result]) -> None:
    print(get_pnlresult_samples)
    assert len(get_pnlresult_samples) > 0