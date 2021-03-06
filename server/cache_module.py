import sys
from datetime import datetime, timedelta, date
import trading_calendars as tc
import pandas_market_calendars as mcal
import pandas as pd
import redis
import time
nyse = mcal.get_calendar('NYSE')
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

a = nyse.valid_days(start_date=str(date.today()), end_date=str(date.today()+timedelta(100)))
TRADING_DAYS = [str(i.date()) for i in a]

def is_cache_good(cache_key):
    d1 = datetime.now()
    curr_date = str(date.today())
    open_time = d1.replace(hour=9)
    open_time = open_time.replace(minute=30)
    close_time = d1.replace(hour=16)
    close_time = close_time.replace(minute=00)
    now_in_sec = int(datetime.utcnow().strftime('%s'))
    print(f'************{cache_key}*****')
    if r.hget(cache_key,'time'):
        if r.hget(curr_date,"trading_date") == "yes" :
            if d1 >= open_time and d1 <= close_time:
                if (now_in_sec - int(r.hget(cache_key,'time'))) < CACHE_TIMEOUT:
                    return True
            elif d1 > close_time and int(r.hget(cache_key,'time')) > int(close_time.strftime('%s')):
                return True
            elif d1 < open_time and (now_in_sec - int(r.hget(cache_key,'time'))) < 3600*4: #4 hours
                return True
            print(r.hget(cache_key,'time'))
            print(close_time.strftime('%s'))
        elif r.hget(curr_date,"trading_date") == "no":
            if (now_in_sec - int(r.hget(cache_key,'time'))) < 3600*10: #update every 10 hours on holidays
                return True
        else:
            check_is_trading()
    return False

def check_is_trading():
    curr_date = str(date.today())
    if curr_date in TRADING_DAYS:
        r.hset(curr_date,"trading_date","yes")
    else:
        r.hset(curr_date,"trading_date","no")
