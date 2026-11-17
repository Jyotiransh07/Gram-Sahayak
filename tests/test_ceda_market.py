"""Offline mock tests. They never contact CEDA or use an API key."""
import pytest
from app import ceda_market


class FakeResponse:
    def __init__(self, data=None, status_code=200, message='OK'):
        self.status_code = status_code
        self._data = {'output': {'type': 'success', 'data': data or [], 'message': message}}

    def json(self):
        return self._data


class FakeSession:
    def __init__(self, status=None):
        self.calls = []
        self.status = status

    def request(self, method, url, headers=None, json=None, timeout=None):
        self.calls.append((method, url, headers, json, timeout))
        if self.status:
            return FakeResponse(status_code=self.status)
        if url.endswith('/commodities'):
            return FakeResponse([{'commodity_id': 42, 'commodity_name': 'Onion'},
                                 {'commodity_id': 77, 'commodity_name': 'Tomato'}])
        if url.endswith('/geographies'):
            return FakeResponse([{'census_state_id': 27, 'census_state_name': 'Maharashtra',
                                  'census_district_id': 516, 'census_district_name': 'Nashik'},
                                 {'census_state_id': 27, 'census_state_name': 'Maharashtra',
                                  'census_district_id': 520, 'census_district_name': 'Pune'}])
        if url.endswith('/markets'):
            return FakeResponse([{'market_id': 9, 'market_name': 'Nashik Mandi'}])
        if url.endswith('/prices'):
            return FakeResponse([
                {'date':'2026-10-14T00:00:00Z', 'commodity_id':42,
                 'census_state_id':27, 'census_district_id':516, 'market_id':9,
                 'min_price':1100, 'max_price':1800, 'modal_price':1400},
                {'date':'2026-10-12T00:00:00Z', 'commodity_id':42,
                 'census_state_id':27, 'census_district_id':516, 'market_id':9,
                 'min_price':1000, 'max_price':1700, 'modal_price':1200},
            ])
        raise AssertionError('Unexpected endpoint: ' + url)


@pytest.fixture(autouse=True)
def no_disk_cache(monkeypatch):
    monkeypatch.setattr(ceda_market.db, 'get_cache', lambda *args, **kwargs: None)
    monkeypatch.setattr(ceda_market.db, 'put_cache', lambda *args, **kwargs: None)


def test_client_bearer_and_lookup():
    session = FakeSession()
    client = ceda_market.CedaClient(api_key='TEST_SECRET', session=session)
    result = client.prices('प्याज़','Maharashtra','Nashik',
                           from_date='2026-01-01', to_date='2026-11-01')
    assert result['provider'].startswith('CEDA')
    assert result['latest_reported_date'] == '2026-10-14'
    assert result['records'][0]['market'] == 'Nashik Mandi'
    assert result['records'][0]['modal_price'] == 1400
    assert result['price_unit'] == 'INR per quintal'
    assert result['record_count'] == 2
    assert not result['cached']
    prices_call = [call for call in session.calls if call[1].endswith('/prices')][0]
    assert prices_call[0] == 'POST'
    assert prices_call[2]['Authorization'] == 'Bearer TEST_SECRET'
    assert prices_call[3]['district_id'] == [516]
    assert prices_call[3]['commodity_id'] == 42
    assert prices_call[3]['state_id'] == 27


def test_invalid_key_does_not_leak_token():
    session = FakeSession(status=401)
    client = ceda_market.CedaClient(api_key='TOP_SECRET', session=session)
    with pytest.raises(ceda_market.CedaError) as info:
        client.commodities()
    assert 'TOP_SECRET' not in str(info.value)
    assert 'rejected' in str(info.value)


def test_ambiguous_or_unknown_commodity():
    session = FakeSession()
    client = ceda_market.CedaClient(api_key='TEST', session=session)
    with pytest.raises(ceda_market.CedaError):
        client.prices('asdfgh','Maharashtra','Nashik',
                      from_date='2026-01-01', to_date='2026-11-01')


def test_invalid_date_range_blocks_request():
    session = FakeSession()
    client = ceda_market.CedaClient(api_key='TEST', session=session)
    with pytest.raises(ceda_market.CedaError):
        client.prices('Onion','Maharashtra','Nashik',
                      from_date='2026-11-01', to_date='2026-01-01')
    assert session.calls == []


def test_no_key():
    with pytest.raises(ceda_market.CedaError):
        ceda_market.CedaClient(api_key='')
