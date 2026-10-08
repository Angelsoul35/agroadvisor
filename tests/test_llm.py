from __future__ import annotations

import pytest

from agroadvisor.llm.base import LLMError, LLMResult
from agroadvisor.llm.cascade import CascadeLLM
from agroadvisor.llm.factory import build_llm
from agroadvisor.llm.fake import FailingLLM, FakeLLM


def test_cascade_falls_back_to_next_provider():
    cascade = CascadeLLM([FailingLLM("a"), FakeLLM("recovered")])
    assert cascade.complete("s", "p").text == "recovered"


def test_cascade_raises_when_all_fail():
    with pytest.raises(LLMError):
        CascadeLLM([FailingLLM("a"), FailingLLM("b")]).complete("s", "p")


def test_cascade_requires_at_least_one_client():
    with pytest.raises(ValueError):
        CascadeLLM([])


def test_factory_builds_cascade_and_single():
    assert build_llm("anthropic,openai").model.startswith("cascade[")
    assert build_llm("ollama").name == "ollama"


def test_factory_rejects_unknown_provider():
    with pytest.raises(ValueError):
        build_llm("nope")


def test_factory_rejects_empty_spec():
    with pytest.raises(ValueError):
        build_llm("   ")


def test_fake_llm_reports_provider_and_model():
    result = FakeLLM("hi").complete("s", "p")
    assert isinstance(result, LLMResult)
    assert result.provider == "fake"
    assert result.model == "fake-1"


def test_fake_llm_accepts_a_callable():
    fake = FakeLLM(lambda system, prompt: prompt.upper())
    assert fake.complete("s", "hello").text == "HELLO"
