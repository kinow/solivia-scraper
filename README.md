# Solivia Scraper

Scraper for Solivia Solar Inverters web site.

## Set up

Clone the project.

    git clone https://github.com/kinow/solivia-scraper.git

Create a dotEnv file

    cd solivia-scraper
    touch .env

Here's an example dotEnv file.

```
SOLIVIA_USER=myemail@myemaildomainname.lo
SOLIVIA_PASS=MyPassWord
SOLIVIA_INVERTERS=comma,separated,list,of,inverters
SOLIVIA_PLANTGUID=my-plant-gui-id
```

You also need to install the project dependencies

    pip install -r requirements.txt

Finally, you can run the scrap.

    python scraper.py --date YYYY-MM-DD

The output will be logged to your console, as in the follow example.

```
user@host$ python scraper.py --date 2016-08-09
2016-08-09 13:58:55,759 Starting Solivia scraper, for date 09/08/2016
2016-08-09 13:58:55,763 Starting new HTTPS connection (1): login.solar-inverter.com
2016-08-09 13:58:58,213 Starting new HTTPS connection (1): monitoring.solar-inverter.com
2016-08-09 13:59:07,054 Time,RPI M10A[1],,,
, AC Power (P1), AC Power (P2), AC Power (P3), Total Power
07:53,"0","0","0","0"
07:58,"0","0","0","0"
08:03,"0.015","0.009","0.022","0.046"
08:08,"0.033","0.023","0.037","0.093"
08:13,"0.042","0.033","0.045","0.12"
08:18,"0.052","0.042","0.052","0.146"
08:23,"0.059","0.05","0.061","0.17"
08:28,"0.065","0.056","0.066","0.187"
...
```

## Usage

You can simply call the script with `python scraper.py`, or you can specify the date
you would like to download the data.

    python scraper.py --date 2016-08-04

Where the format is YYYY-MM-DD (i.e. year with four digits, month with two digits, and
finally day with two digits too).

The complete usage:

```
usage: scraper.py [-h] [--date DATE] [--from FROM_] [--to TO] --types TYPES
                  [--interval INTERVAL]

Solivia Monitoring scraper

optional arguments:
  -h, --help           show this help message and exit
  --date DATE          Date (YYYY-mm-dd)
  --from FROM_         Date (YYYY-mm-dd)
  --to TO              Date (YYYY-mm-dd)
  --types TYPES        Comma separated types e.g. Power,Energy,AcParam,DcParam
  --interval INTERVAL  Being nice to servers, and waiting for an interval in
                       milliseconds before firing more requests (defaults to
                       300)

the --date parameter is exclusive to --to and --from. If --date is used, then
the others will be ignored
```

## Output

For every time you execute the script, you should see two files in your script directory.
One CSV and one JSON file, named with the timestamp for the date used to retrieve data.

Examples:

* 20160809000000.csv
* 20160809000000.json

The names will match.
