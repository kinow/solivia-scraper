#!/usr/bin/env python3

"""
A simple script, not distributed via pypi, that collects data from
the Solivia Monitoring web sites. Other solutions include changing
the way the device communicates to the servers, by intercepting
calls via serial communication modifications. This approach is useful
for those who cannot change the device. Licensed under the MIT
License.
"""

import os, sys
import requests
from datetime import datetime, timedelta
import urllib
import re
import html
import time
# JSON
import json
# CSV
import csv
# parsing HTML
from html.parser import HTMLParser
# parameters
import argparse
parser = argparse.ArgumentParser(description='Solivia Monitoring scraper', epilog='the --date parameter is exclusive to --to and --from. If --date is used, then the others will be ignored')
parser.add_argument('--date', help='Date (YYYY-mm-dd)', type=lambda s: datetime.strptime(s, '%Y-%m-%d'), default=None)
parser.add_argument('--from', dest="from_", help='Date (YYYY-mm-dd)', type=lambda s: datetime.strptime(s, '%Y-%m-%d'), default=None)
parser.add_argument('--to', help='Date (YYYY-mm-dd)', type=lambda s: datetime.strptime(s, '%Y-%m-%d'), default=None)
parser.add_argument('--types', help='Comma separated types e.g. Power,Energy,AcParam,DcParam', type=lambda s: s.lower().replace(' ', '').split(','), required=True)
parser.add_argument('--interval', help='Being nice to servers, and waiting for an interval in milliseconds before firing more requests (defaults to 300)', type=int, default=300)
# loggin imports
import logging
from pprint import pprint
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s')
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
# dotEnv imports
from os.path import join, dirname
from dotenv import load_dotenv

class MyHTMLParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)
        self.url = None

    def handle_starttag(self, tag, attrs):
        if tag == 'form':
            for attr in attrs:
                if attr[0] == 'action':
                    self.url = attr[1]

    def handle_endtag(self, tag):
        pass

    def handle_data(self, data):
        pass

    def get_url(self):
        return self.url

def get_headers():
    # Specify Google Chrome user agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36',
    }
    return headers

def get(session, url):
    """Utility method to HTTP GET a URL"""
    response = session.get(url, timeout=None, headers=get_headers())
    logging.debug("### GET to %s" % url)
    if response.status_code != requests.codes.ok:
        response.raise_for_status()
    logging.debug(response.text)
    return response

def post(session, url, data):
    """Utility method to HTTP POST a URL with data parameters"""
    response = session.post(url, data=data, timeout=None, headers=get_headers())
    logging.debug("### POST to %s" % url)
    logging.debug(response.text)
    if response.status_code != requests.codes.ok:
        response.raise_for_status()
    return response

def get_inverters_string(inverters_array):
    inverters = '%3B'.join(inverters_array)
    return inverters

def get_wresult_string(text_with_ws_result):
    if text_with_ws_result == None or text_with_ws_result.strip() == '':
        raise Exception("Missing the text with WSRESULT!")
    logging.info("Searching for wresult...")
    search_result = re.search('<input type="hidden" name="wresult" value="(.*)" />\s*<input type="hidden" name="wctx"', text_with_ws_result)
    if search_result != None:
        token = search_result.group(1)
        wresult = html.unescape(token)
        return wresult
    raise Exception("Could not find WRESULT string!")

def get_form_action(response_txt):
    logging.info("Searching for form action...")
    parser = MyHTMLParser()
    parser.feed(response_txt)
    url = parser.get_url()
    return "%s" % (url)

def main():
    """Main method"""

    args            = parser.parse_args()
    if args.date != None:
        date            = args.date.replace(hour=0, minute=0, second=0, microsecond=0)
        from_date       = date
        to_date         = date
    else:
        from_date       = args.from_.replace(hour=0, minute=0, second=0, microsecond=0)
        to_date         = args.to.replace(hour=0, minute=0, second=0, microsecond=0)

    types           = args.types
    interval        = args.interval

    logging.info("Starting Solivia scraper")
    logging.info("Types selected: %s" % (', '.join(types)))
    logging.info("Date interval: %s to %s" % (from_date.strftime("%Y-%m-%d"), to_date.strftime("%Y-%m-%d")))

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
        sign_in_url = 'https://monitoring.solar-inverter.com/'
        r = get(s, sign_in_url)
        login_url = get_form_action(r.text)
        logging.info('--> Log in URL found: %s' % login_url)

        data = {'username': SOLIVIA_USER, 'password': SOLIVIA_PASS}
        logging.debug("Logging in...")
        r = post(s, login_url, data)

        # Azure AD auth
        wresult = get_wresult_string(r.text)
        data = {'wa': 'wsignin1.0', 'wresult': wresult, 'wctx': 'rm=0&id=passive&ru=%2f'}
        logging.debug("Azure AD authentication...")
        r = post(s, 'https://monitoring.solar-inverter.com/', data)

        # 1 day each time
        step = timedelta(days=1)

        while from_date <= to_date:
            date_formatted  = from_date.strftime('%d/%m/%Y')
            logging.info("Download data for date %s..." % date_formatted)
            date_encoded    = urllib.parse.quote_plus(date_formatted)
        
            # Set X config
            set_date_url = "https://monitoring.solar-inverter.com/Chart/SetXConfig?date=%s" % date_encoded
            logging.debug("Setting the context date...")
            r = get(s, set_date_url)

            for t in types:
                logging.info("Downloading %s data..." % t)
                title_type = t.title()

                # Fetch inverter data
                fetch_inverter_data_url = 'https://monitoring.solar-inverter.com/Chart/FetchInverterData?duration=Daily&type=' + title_type
                data = {'sort': '', 'group': '', 'filter': '', 'duration': 'Daily'}
                logging.debug("Fetching the data...")
                r = post(s, fetch_inverter_data_url, data)

                # Define inverters selected
                update_selected_inverters_url = 'https://monitoring.solar-inverter.com/Chart/UpdateInverterSelection?invList=' + inverters
                logging.debug("Updating selected inverters...")
                r = get(s, update_selected_inverters_url)

                # Set X config (again, as the UI does that)
                set_date_url = "https://monitoring.solar-inverter.com/Chart/SetXConfig?date=%s" % date_encoded
                logging.debug("Setting the context date...")
                r = get(s, set_date_url)

                # Set Y config
                set_parameters_url = 'https://monitoring.solar-inverter.com/Chart/SetYConfig?invList=' + inverters + '%3B&dataType=' + title_type + '&yMult=1'
                logging.debug("Setting other parameters, including inverters...")
                r = get(s, set_parameters_url)

                # Get data URL + the Solivia plant GUID
                get_data_url = "https://monitoring.solar-inverter.com/Chart/FetchChartData?duration=Daily&datatype=%s&plantGuid=%s" % (title_type, SOLIVIA_PLANTGUID)
                logging.debug("Retrieving the Solar Inverters data...")
                r = get(s, get_data_url)

                # Will fail if invalid JSON
                data = json.loads(r.text)
                logging.debug(data)

                destination_file = join(dirname(__file__), from_date.strftime('%Y%m%d'))

                # Write JSON
                j = json.loads(r.text)
                values = []
                for temp_i in j:
                    for temp_j in temp_i:
                        obj = temp_j
                        obj['date'] = date_formatted
                        values.append(obj)
                with open(destination_file + '-' + t + '.json', 'w', newline='\n') as out_file:
                    out_file.write(r.text)

                # Get CSV data
                get_csv_url = "https://monitoring.solar-inverter.com/Chart/ExportChartData?duration=Daily&dataType=%s&plantGuid=%s" % (title_type, SOLIVIA_PLANTGUID)
                r = get(s, get_csv_url)

                # Write CSV
                with open(destination_file + '-' + t + '.csv', 'w', newline='\n') as out_file:
                    out_file.write(r.text)

                logging.debug(r.text)

                # sleep
                if from_date != to_date:
                    float_interval = (interval / 1000)
                    logging.debug("Sleeping for %f milli seconds" % float_interval)
                    time.sleep(float_interval)

            # Next day...
            from_date += step

        logging.info("All done! Bye!")

if __name__ == '__main__':
    """App entry point"""
    main()
