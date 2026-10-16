import json
from types import SimpleNamespace

import httpx
import pytest

from app import advisor, tools


def test_unknown_tool_and_bad_args():
    assert "Unknown tool" in tools.run_tool("rm_rf", "{}")
    assert "Invalid arguments" in tools.run_tool("convert_currency", "not json")
    assert "Invalid arguments" in tools.run_tool("convert_currency", '{"amount": 1}')


def test_currency_validation_and_alias(monkeypatch):
    seen = {}

    def fake_get(url, params, timeout):
        seen.update(params)
        return httpx.Response(200, json={"date": "2026-10-16", "rates": {"TRY": 50.0}},
                              request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    out = json.loads(tools.run_tool("convert_currency",
                                    json.dumps({"amount": 10, "from_currency": "eur", "to_currency": "TL"})))
    assert out["result"] == 500.0
    assert seen == {"base": "EUR", "symbols": "TRY"}
    bad = json.loads(tools.run_tool("convert_currency",
                                    json.dumps({"amount": 1, "from_currency": "EUR", "to_currency": "JPY"})))
    assert "Supported currencies" in bad["error"]
    same = json.loads(tools.run_tool("convert_currency",
                                     json.dumps({"amount": 5, "from_currency": "USD", "to_currency": "USD"})))
    assert same["result"] == 5


def test_weather(monkeypatch):
    def fake_get(url, params, timeout):
        if "geocoding" in url:
            body = {"results": [{"name": "Lisbon", "country": "Portugal", "latitude": 1, "longitude": 2}]}
        else:
            body = {"daily": {"time": ["2026-10-17"], "weather_code": [61], "temperature_2m_max": [20.0],
                              "temperature_2m_min": [14.0], "precipitation_probability_max": [70]}}
        return httpx.Response(200, json=body, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    out = json.loads(tools.run_tool("get_weather", '{"city": "Lisbon", "days": 99}'))
    assert out["city"] == "Lisbon"
    assert out["forecast"][0]["summary"] == "light rain"


def test_external_failure_is_safe(monkeypatch):
    def boom(url, params, timeout):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "get", boom)
    out = json.loads(tools.run_tool("get_weather", '{"city": "Lisbon"}'))
    assert "unavailable" in out["error"]


def test_translate_validation():
    assert "Supported languages" in tools.run_tool("translate", '{"text": "hi", "target_language": "fr"}')
    long = json.dumps({"text": "x" * 5000, "target_language": "de"})
    assert "characters" in tools.run_tool("translate", long)


def test_translate_calls_model(monkeypatch):
    fake = SimpleNamespace(responses=SimpleNamespace(
        create=lambda **kw: SimpleNamespace(output_text=" Guten Tag ")))
    monkeypatch.setattr(tools, "get_client", lambda: fake)
    out = json.loads(tools.run_tool("translate", '{"text": "Good day", "target_language": "de"}'))
    assert out == {"target_language": "de", "translation": "Guten Tag"}


def _resp(rid, output, text="", inp=10, outp=5):
    return SimpleNamespace(id=rid, output=output, output_text=text,
                           usage=SimpleNamespace(input_tokens=inp, output_tokens=outp))


def test_chat_tool_loop(monkeypatch):
    calls = []
    tool_call = SimpleNamespace(type="function_call", call_id="c1", name="convert_currency",
                                arguments='{"amount": 1, "from_currency": "EUR", "to_currency": "USD"}')
    replies = [_resp("r1", [tool_call]), _resp("r2", [], text="1 EUR = 1.12 USD")]

    def create(**kw):
        calls.append(kw)
        return replies[len(calls) - 1]

    monkeypatch.setattr(advisor, "_client", lambda: SimpleNamespace(responses=SimpleNamespace(create=create)))
    monkeypatch.setattr(tools, "run_tool", lambda n, a: '{"result": 1.12}')
    answer, rid, call, total = advisor.chat("How much is 1 EUR in USD?", None)
    assert answer == "1 EUR = 1.12 USD" and rid == "r2"
    assert call.input_tokens == 20 and call.output_tokens == 10
    assert calls[1]["previous_response_id"] == "r1"
    assert calls[1]["input"][0]["type"] == "function_call_output"


def test_chat_tool_loop_is_bounded(monkeypatch):
    n = []
    tool_call = SimpleNamespace(type="function_call", call_id="c", name="get_weather", arguments="{}")

    def create(**kw):
        n.append(kw["tool_choice"])
        return _resp(f"r{len(n)}", [tool_call] if kw["tool_choice"] == "auto" else [], text="done")

    monkeypatch.setattr(advisor, "_client", lambda: SimpleNamespace(responses=SimpleNamespace(create=create)))
    monkeypatch.setattr(tools, "run_tool", lambda n_, a: "{}")
    answer, *_ = advisor.chat("weather?", None)
    assert answer == "done"
    assert n[-1] == "none" and len(n) == advisor.MAX_TOOL_ROUNDS + 1
