import json
import pytest
from app import db, rag, tools


def test_hindi_and_english_database(tmp_path):
    session = 'test-' + tmp_path.name
    db.store_message(session, 'user', 'नमस्ते', 'hi')
    assert db.get_history(session)[-1]['content'] == 'नमस्ते'
    assert db.save_profile(session, 'Nashik', '', 'Wheat', 'hi', consent=False) is False
    assert db.get_profile(session) is None
    assert db.save_profile(session, 'Nashik', '', 'Wheat', 'hi', consent=True)
    assert db.get_profile(session)['language'] == 'hi'
    db.delete_user_data(session)
    assert not db.get_history(session)


def test_text_chunks_and_grounding():
    chunks = rag.split_text('Agriculture. ' * 200, max_chars=100, overlap=20)
    assert len(chunks) >= 3
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert rag.split_text(' ') == []


def test_scheme_directory_uses_real_portals():
    record = tools.schemes('crop insurance').get('data')
    assert record['schemes']
    assert record['schemes'][0]['url'].startswith('https://')


# CEDA_PATCH_V1: integration now requires CEDA_API_KEY, not DATA_GOV_API_KEY.
def test_mandi_requires_ceda_key(monkeypatch):
    monkeypatch.setenv('CEDA_API_KEY', '')
    monkeypatch.setattr(tools.db, 'get_cache', lambda *args: None)
    with pytest.raises(tools.ToolError, match='CEDA API key missing'):
        tools.mandi('Onion')


def test_bad_climate_year():
    # The year restriction applies after resolving a city, so mock the coordinates.
    original = tools.location_coordinates
    tools.location_coordinates = lambda _: {'latitude': 20, 'longitude': 73, 'name': 'Nashik'}
    try:
        with pytest.raises(tools.ToolError, match='completed year'):
            tools.climate('Nashik', year=2099)
    finally:
        tools.location_coordinates = original


def test_weather_realistic_fields_with_mock(monkeypatch):
    monkeypatch.setattr(tools, 'location_coordinates', lambda _: {
        'latitude': 10, 'longitude': 70, 'name': 'Demo', 'state': 'Test State'})
    monkeypatch.setattr(db, 'get_cache', lambda *args: None)
    monkeypatch.setattr(db, 'put_cache', lambda *args: None)
    monkeypatch.setattr(tools, 'get_json', lambda *args, **kwargs: (
        {'current':{'time':'2026-11-17T12:00','temperature_2m':30,
                    'relative_humidity_2m':70,'precipitation':0,'wind_speed_10m':4},
         'daily': {'time':['2026-11-17']}},
        'https://api.open-meteo.com/v1/forecast'))
    result = tools.weather('Demo')
    assert '30 °C' in result['text']
    assert result['title'] == 'Open-Meteo forecast'


def test_agent_routing_and_verification():
    pytest.importorskip('langgraph')
    from app.workflow import route_by_rules, triage, verifier
    assert route_by_rules('कल मौसम कैसा है?') == 'weather'
    assert route_by_rules('How much is onion mandi price?') == 'mandi'
    assert route_by_rules('Historical climate 2025') == 'climate'
    assert route_by_rules('any', 'photo.jpg') == 'vision'
    urgent = triage({'query': 'Someone has chest pain', 'language':'en', 'trace':[]})
    assert urgent['emergency'] and '112' in urgent['answer']
    verified = verifier({'answer': 'Forecast 45 degrees', 'evidence': [{'text':'20 degrees'}], 'tries':0, 'trace':[]})
    assert verified['verified'] is False
    assert '45' in verified['feedback']
