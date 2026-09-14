import pytest

from collectors.axis3_canary_floor import confirmation, main


def test_baseline_confirms_unchanged_floor(capsys):
    result = confirmation()
    assert (result["cohort"], result["p"], result["n"]) == ("coding-agents", 0.909, 11)
    assert result["lower"] == pytest.approx(0.822282590780)
    assert result["floor"] == 0.80 and result["confirmed"]
    assert main() == 0
    assert "CONFIRM floor 0.80" in capsys.readouterr().out
