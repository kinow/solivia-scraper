#!/usr/bin/env python3
# TODO: docs

import os, sys
import requests
from pprint import pprint
from datetime import datetime
import urllib
import re
import html

def main():

    now = datetime.now()
    now_ts = now.strftime('%Y-%m-%dT%H:%M:%SZ') #2016-08-08T03:38:25Z
    now_ts2 = now.strftime('%Y-%m-%dT%H:%M:%S.000Z') #2016-08-08T03:38:25Z
    now_ts_enc = urllib.parse.quote_plus(urllib.parse.quote_plus(urllib.parse.quote_plus(now_ts)))
    now_ts_enc2 = urllib.parse.quote_plus(urllib.parse.quote_plus(urllib.parse.quote_plus(now_ts2)))

    # TODO parameterise, and dotEnv

    login_url = 'https://login.solar-inverter.com/en-US/Account/SignIn?returnUrl=%252fissue%252fwsfed%253fwa%253dwsignin1.0%2526wtrealm%253dhttp%25253a%25252f%25252fsoliviamonitoring.com%25252f%2526wctx%253drm%25253d0%252526id%25253dpassive%252526ru%25253d%2525252f%2526wct%253d' + now_ts_enc
    user = ''
    password = ''

    inverter1 = ''
    inverter2 = ''
    plant_guid = ''

    # Log in
    with requests.Session() as s:
        r = s.post(login_url, data={'Email': user, 'Password': password, 'RememberMe': 'false'})
        if r.status_code != requests.codes.ok:
            r.raise_for_status()

        redirect_url = 'https://login.solar-inverter.com/issue/wsfed?wa=wsignin1.0&wtrealm=http%3a%2f%2fsoliviamonitoring.com%2f&wctx=rm%3d0%26id%3dpassive%26ru%3d%252f&wct=' + now_ts_enc
        # Redirect post login
        r = s.get(redirect_url)
        if r.status_code != requests.codes.ok:
            r.raise_for_status()
        text_with_ws_result = r.text

        # Crazy auth
        wresult = re.search('%s(.*)%s' % ('<input type="hidden" name="wresult" value="', '" /><input type="hidden" name="wctx"'), text_with_ws_result).group(1)
        wresult = html.unescape(wresult)
        print(wresult)
        r = s.post('https://monitoring.solar-inverter.com/', data={'wa': 'wsignin1.0', 'wresult': wresult, 'wctx': 'rm=0&id=passive&ru=%2f'})
        if r.status_code != requests.codes.ok:
            r.raise_for_status()

        set_date_url = 'https://monitoring.solar-inverter.com/Chart/SetXConfig?date=06%2F08%2F2016'
        fetch_inverter_data_url = 'https://monitoring.solar-inverter.com/Chart/FetchInverterData?duration=Daily'
        set_parameters_url = 'https://monitoring.solar-inverter.com/Chart/SetYConfig?invList=' + inverter1 + '%3B' + inverter2 + '%3B&dataType=Power&yMult=1'
        get_data_url = 'https://monitoring.solar-inverter.com/Chart/FetchChartData?duration=Daily&datatype=Power&plantGuid=' + plant_guid

        # Set date
        r = s.get(set_date_url)
        if r.status_code != requests.codes.ok:
            r.raise_for_status()

        # Fetch inverter data
        r = s.post(fetch_inverter_data_url, data={'sort': '', 'group': '', 'filter': '', 'duration': 'Daily'})
        if r.status_code != requests.codes.ok:
            r.raise_for_status()

        # Set other parameters
        r = s.get(set_parameters_url)
        if r.status_code != requests.codes.ok:
            r.raise_for_status()

        # Get data
        r = s.get(get_data_url)
        if r.status_code != requests.codes.ok:
            r.raise_for_status

        print(r.text)

if __name__ == '__main__':
    main()