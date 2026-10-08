from __future__ import annotations

import pytest

from agroadvisor import cli, service
from agroadvisor.llm.fake import FailingLLM


@pytest.fixture(autouse=True)
def offline_llm(monkeypatch):
    # The CLI builds its own service; force the offline path so no network is used.
    monkeypatch.setattr(service, "build_llm", lambda spec: FailingLLM())


def test_demo_runs_and_shows_computed_numbers(capsys):
    assert cli.main(["demo"]) == 0
    out = capsys.readouterr().out
    assert "AgroAdvisor demo" in out
    # Scenario 1: dry-spell maize, net irrigation 2.95 mm (recomputed in engine tests).
    assert "net irrigation=2.95" in out
    # Scenario 3: the high-humidity case must be flagged HIGH for late blight.
    assert "HIGH" in out
    assert "Late blight" in out
    # Every scenario prints the offline advisory.
    assert "advisory [template]" in out


def test_main_usage_without_command(capsys):
    assert cli.main([]) == 1
    assert "usage" in capsys.readouterr().out.lower()
