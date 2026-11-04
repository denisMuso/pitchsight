import httpx
import pytest

from pitchsight.data.provider import FootballData, ProviderError


def test_credentials_required(monkeypatch):
    monkeypatch.delenv("FOOTBALL_DATA_TOKEN", raising=False)
    with pytest.raises(ProviderError, match="required"):
        FootballData()


def test_bounded_retry_and_forbidden():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "0"})

    client = FootballData("test", httpx.MockTransport(handler), interval=0, sleep=lambda _: None)
    with pytest.raises(ProviderError, match="limit"):
        client.get("competitions/PL/matches")
    assert len(calls) == 4
    client.close()
    client = FootballData("test", httpx.MockTransport(lambda _: httpx.Response(403)), interval=0)
    with pytest.raises(ProviderError, match="subscription"):
        client.get("competitions/CL/matches")
    client.close()
