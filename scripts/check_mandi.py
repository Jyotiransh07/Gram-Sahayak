"""Connection test that never prints the secret government API key."""
import requests
from app import config

if not config.DATA_GOV_KEY or not config.DATA_GOV_RESOURCE:
    print('Missing DATA_GOV_API_KEY or DATA_GOV_RESOURCE_ID in .env')
else:
    url = f'https://api.data.gov.in/resource/{config.DATA_GOV_RESOURCE}'
    params = {'api-key': config.DATA_GOV_KEY, 'format': 'json', 'limit': 1}
    print('Testing government resource access (no secret is printed)...')
    try:
        r = requests.get(url, params=params, timeout=(5, 12))
        print('HTTP status:', r.status_code)
        if r.ok:
            payload = r.json()
            records = payload.get('records') if isinstance(payload, dict) else None
            print('Records returned:', len(records) if isinstance(records, list) else 'not present')
            if isinstance(records, list) and records:
                print('API connectivity and data retrieval work.')
        else:
            print('Government server responded, but did not approve or process the request.')
    except requests.Timeout:
        print('TIMEOUT: Government server did not respond in time. Retry later.')
    except requests.ConnectionError:
        print('CONNECTION ERROR: Check network, DNS, firewall, or government service availability.')
    except (requests.RequestException, ValueError):
        print('REQUEST ERROR: Government API did not return usable data.')
