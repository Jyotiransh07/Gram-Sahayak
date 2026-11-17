"""Check CEDA API connectivity without printing secrets. Run: python -m scripts.check_ceda"""
from app.ceda_market import CedaClient, CedaError


def main():
    try:
        cli = CedaClient()
        crops = cli.commodities()
        print('CEDA API authentication and commodity lookup: OK')
        print('Commodities available:', len(crops))
        places = cli.geographies()
        print('Geographies available:', len(places))
        try:
            result = cli.prices('Onion','Maharashtra','Nashik')
            print('PRICE CHECK OK')
            print('Latest reported date:', result['latest_reported_date'])
            print('Record count:', result['record_count'])
            print('Example reported row:', result['records'][0])
        except CedaError as exc:
            print('Catalog works, but sample price query was unsuccessful:', exc)
            print('Try a different district or a wider date range in the app.')
    except CedaError as exc:
        print('CEDA API diagnostic failed:', exc)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
