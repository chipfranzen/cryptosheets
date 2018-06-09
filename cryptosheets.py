#!/usr/bin/env python
import csv
import httplib2
import os

import pandas as pd
import requests
import yaml

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-crypto-market-cap.json
with open('cryptosheets.yaml') as f:
    config = yaml.load(f)

SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_SECRET_FILE = config['CLIENT_SECRET_FILE']
APPLICATION_NAME = config['APPLICATION_NAME']


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-crypto-market-cap.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def main():
    print('requesting crypto market data...')
    prices = requests.get('https://api.coinmarketcap.com/v1/ticker/')
    price_df = pd.DataFrame(prices.json())
    market_cap = requests.get('https://api.coinmarketcap.com/v1/global/')
    print(' done!')
    total_market_cap = market_cap.json()['total_market_cap_usd']
    price_df['percent_total_market'] = price_df.market_cap_usd.apply(float) / total_market_cap
    write_df = price_df[['rank',
                         'id',
                         'name',
                         'symbol',
                         'price_btc',
                         'price_usd',
                         'percent_total_market']]
    write_df = write_df.sort_values(by='percent_total_market')
    print(f'the cryptocurrency with the biggest market cap today is: {write_df['name'][0]}')
    print('writing to `./prices.csv`...')
    write_df.to_csv('prices.csv', index=False)
    print(' done!')
    print('reading csv...')
    with open('prices.csv') as f:
        price_reader = csv.reader(f)
        data = [v for v in price_reader]
    print(' done!')
    print('authorizing credentials...')
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    print(' done!')
    print('writing to google sheets...')
    service = discovery.build('sheets', 'v4', http=http)

    spreadsheetId = config['spreadsheetId']
    range_name = 'Sheet1!R2:X12'
    request_body = {
        'range': range_name,
        'values': data[:11]
    }
    result = service.spreadsheets().values().update(spreadsheetId=spreadsheetId, body=request_body, range=range_name, valueInputOption='USER_ENTERED').execute()
    print(' done! {0} cells updated.'.format(result.get('updatedCells')));

if __name__ == '__main__':
    main()
