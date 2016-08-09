#!/usr/bin/env python3
# TODO: docs

import os, sys
import requests
from datetime import datetime
import urllib
import re
import html
import json
# parameters
import argparse
parser = argparse.ArgumentParser(description='Solivia Monitoring scraper')
parser.add_argument('--date', help='Date (YYYY-mm-dd)', type=lambda s: datetime.strptime(s, '%Y-%m-%d'), default=datetime.now())
# loggin imports
import logging
from pprint import pprint
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
# dotEnv imports
from os.path import join, dirname
from dotenv import load_dotenv

def get(session, url):
    """Utility method to HTTP GET a URL"""
    response = session.get(url)
    if response.status_code != requests.codes.ok:
        response.raise_for_status()
    return response

def post(session, url, data):
    """Utility method to HTTP POST a URL with data parameters"""
    response = session.post(url, data=data)
    if response.status_code != requests.codes.ok:
        response.raise_for_status()
    return response

def get_inverters_string(inverters_array):
    inverters = '%3B'.join(inverters_array)
    return inverters

def get_wresult_string(text_with_ws_result):
    token = re.search('%s(.*)%s' % ('<input type="hidden" name="wresult" value="', '" /><input type="hidden" name="wctx"'), text_with_ws_result).group(1)
    wresult = html.unescape(token)
    return wresult

def main():
    """Main method"""

    args            = parser.parse_args()
    date            = args.date
    date_formatted  = date.strftime('%d/%m/%Y')
    logging.info("Starting Solivia scraper, for date %s" % date_formatted)
    date_encoded    = urllib.parse.quote_plus(date_formatted)

    # dotEnv
    logging.debug("Loading dotEnv file .env")
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)

    # environment data
    SOLIVIA_USER        = os.environ.get('SOLIVIA_USER')
    SOLIVIA_PASS        = os.environ.get('SOLIVIA_PASS')
    SOLIVIA_INVERTERS   = os.environ.get('SOLIVIA_INVERTERS').split(',')
    SOLIVIA_PLANTGUID   = os.environ.get('SOLIVIA_PLANTGUID')

    logging.debug("Inverters: %s" % ', '.join(SOLIVIA_INVERTERS))

    # date time parameters for auth. The now_ts_enc variable is used on the login post
    # and in the redirect post
    now         = datetime.now()
    now_ts      = now.strftime('%Y-%m-%dT%H:%M:%SZ') #2016-08-08T03:38:25Z
    now_ts_enc  = urllib.parse.quote_plus(urllib.parse.quote_plus(urllib.parse.quote_plus(now_ts)))

    inverters = get_inverters_string(SOLIVIA_INVERTERS)

    # Start a requests session. The session takes care of passing the cookies
    # to the next requests.
    logging.debug("Starting requests session")
    with requests.Session() as s:
        # Sign in
        login_url = 'https://login.solar-inverter.com/en-US/Account/SignIn?returnUrl=%252fissue%252fwsfed%253fwa%253dwsignin1.0%2526wtrealm%253dhttp%25253a%25252f%25252fsoliviamonitoring.com%25252f%2526wctx%253drm%25253d0%252526id%25253dpassive%252526ru%25253d%2525252f%2526wct%253d' + now_ts_enc
        data = {'Email': SOLIVIA_USER, 'Password': SOLIVIA_PASS, 'RememberMe': 'false'}
        logging.debug("Logging in...")
        r = post(s, login_url, data)

        # Redirect post login
        redirect_url = 'https://login.solar-inverter.com/issue/wsfed?wa=wsignin1.0&wtrealm=http%3a%2f%2fsoliviamonitoring.com%2f&wctx=rm%3d0%26id%3dpassive%26ru%3d%252f&wct=' + now_ts_enc
        logging.debug("Following log in redirect...")
        r = get(s, redirect_url)
        text_with_ws_result = r.text

        # Azure AD auth
        wresult = get_wresult_string(text_with_ws_result)
        data = {'wa': 'wsignin1.0', 'wresult': wresult, 'wctx': 'rm=0&id=passive&ru=%2f'}
        logging.debug("Azure AD authentication...")
        r = post(s, 'https://monitoring.solar-inverter.com/', data)

        # Fetch inverter data
        fetch_inverter_data_url = 'https://monitoring.solar-inverter.com/Chart/FetchInverterData?duration=Daily'
        data = {'sort': '', 'group': '', 'filter': '', 'duration': 'Daily'}
        logging.debug("Fetching the data...")
        r = post(s, fetch_inverter_data_url, data)

        # Set X config
        set_date_url = "https://monitoring.solar-inverter.com/Chart/SetXConfig?date=%s" % date_encoded
        logging.debug("Setting the context date...")
        r = get(s, set_date_url)

        # Set Y config
        set_parameters_url = 'https://monitoring.solar-inverter.com/Chart/SetYConfig?invList=' + inverters + '%3B&dataType=Power&yMult=1'
        logging.debug("Setting other parameters, including inverters...")
        r = get(s, set_parameters_url)

        get(s, 'https://monitoring.solar-inverter.com/Chart/UpdateInverterSelection?invList=20632dbb-2031-4c03-8203-1a6bea924dff%3B')

        # Get data URL + the Solivia plant GUID
        get_data_url = "https://monitoring.solar-inverter.com/Chart/FetchChartData?duration=Daily&datatype=Power&plantGuid=%s" % SOLIVIA_PLANTGUID
        logging.debug("Retrieving the Solar Inverters data...")
        r = get(s, get_data_url)

        # Will fail if invalid JSON
        data = json.loads(r.text)
        logging.debug(data)

        destination_file = join(dirname(__file__), date.strftime('%Y%m%d%H%M%S'))

        # Write JSON
        with open(destination_file + '.json', 'w') as out_file:
            out_file.write(r.text)

        # Get CSV data
        get_csv_url = "https://monitoring.solar-inverter.com/Chart/ExportChartData?duration=Daily&dataType=Power&plantGuid=%s" % SOLIVIA_PLANTGUID
        r = get(s, get_csv_url)

        # Write CSV
        with open(destination_file + '.csv', 'w') as out_file:
            out_file.write(r.text)

        logging.info(r.text)

        logging.info("All done! Bye!")

if __name__ == '__main__':
    """App entry point"""
    main()
