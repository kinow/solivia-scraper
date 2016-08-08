#!/usr/bin/env python3
# TODO: docs

import os, sys
import requests
from datetime import datetime
import urllib
import re
import html
# loggin imports
import logging
from pprint import pprint
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
# dotEnv imports
from os.path import join, dirname
from dotenv import load_dotenv

def get(session, url):
    """Utility method to HTTP GET a URL"""
    response = s.get(url)
    if response.status_code != requests.codes.ok:
        response.raise_for_status()
    return 

def post(session, url, data):
    """Utility method to HTTP POST a URL with data parameters"""
    response = s.post(url, data=data)
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

    logging.info("Starting Solivia scraper")

    # dotEnv
    logging.debug("Loading dotEnv file .env")
    dotenv_path = join(dirname(__file__), '.env')
    load_dotenv(dotenv_path)

    # environment data
    SOLIVIA_USER        = os.environ.get('SOLIVIA_USER')
    SOLIVIA_PASS        = os.environ.get('SOLIVIA_PASS')
    SOLIVIA_INVERTERS   = os.environ.get('SOLIVIA_INVERTERS').split(',')
    SOLIVIA_PLANTGUID   = os.environ.get('SOLIVIA_PLANTGUID')

    logging.debug("Inverters: %s" % ','.join(SOLIVIA_INVERTERS))

    # date time parameters for auth. The now_ts_enc variable is used on the login post
    # and in the redirect post
    now         = datetime.now()
    now_ts      = now.strftime('%Y-%m-%dT%H:%M:%SZ') #2016-08-08T03:38:25Z
    now_ts_enc  = urllib.parse.quote_plus(urllib.parse.quote_plus(urllib.parse.quote_plus(now_ts)))

    # Start a requests session. The session takes care of passing the cookies
    # to the next requests.
    with requests.Session() as s:
        # Log in
        login_url = 'https://login.solar-inverter.com/en-US/Account/SignIn?returnUrl=%252fissue%252fwsfed%253fwa%253dwsignin1.0%2526wtrealm%253dhttp%25253a%25252f%25252fsoliviamonitoring.com%25252f%2526wctx%253drm%25253d0%252526id%25253dpassive%252526ru%25253d%2525252f%2526wct%253d' + now_ts_enc
        data = {'Email': SOLIVIA_USER, 'Password': SOLIVIA_PASS, 'RememberMe': 'false'}
        r = post(s, login_url, data)

        # Redirect post login
        redirect_url = 'https://login.solar-inverter.com/issue/wsfed?wa=wsignin1.0&wtrealm=http%3a%2f%2fsoliviamonitoring.com%2f&wctx=rm%3d0%26id%3dpassive%26ru%3d%252f&wct=' + now_ts_enc
        r = get(s, redirect_url)
        text_with_ws_result = r.text

        # Azure AD auth
        wresult = get_wresult_string(text_with_ws_result)
        data = {'wa': 'wsignin1.0', 'wresult': wresult, 'wctx': 'rm=0&id=passive&ru=%2f'}
        r = post(s, 'https://monitoring.solar-inverter.com/', data)

        # Set the context date
        set_date_url = 'https://monitoring.solar-inverter.com/Chart/SetXConfig?date=06%2F08%2F2016'
        r = get(s, set_date_url)

        # Fetch inverter data
        fetch_inverter_data_url = 'https://monitoring.solar-inverter.com/Chart/FetchInverterData?duration=Daily'
        data = {'sort': '', 'group': '', 'filter': '', 'duration': 'Daily'}
        r = post(s, fetch_inverter_data_url, data)

        # Set other parameters, including inverters
        inverters = get_inverters_string(SOLIVIA_INVERTERS)
        set_parameters_url = 'https://monitoring.solar-inverter.com/Chart/SetYConfig?invList=' + inverters + '%3B&dataType=Power&yMult=1'
        r = get(s, set_parameters_url)

        # Get data URL + the Solivia plant GUID
        get_data_url = "https://monitoring.solar-inverter.com/Chart/FetchChartData?duration=Daily&datatype=Power&plantGuid=%s" % SOLIVIA_PLANTGUID
        r = get(s, get_data_url)

        print(r.text)

if __name__ == '__main__':
    """App entry point"""
    main()
