import sys
from datetime import datetime, timedelta, date
import pandas as pd
import ast
import redis
import time
from datetime import datetime, timedelta
#from cache_module import check_is_trading
from calc_module import range_data_from_symbol, prob_move_pct,  amt_to_invest, check_is_trading, best_call_trades
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
CACHE_TIMEOUT = 1500
SYMBOL_LIST = ["AAL","AAPL","ABBV","ACB","AI","AMC","AMD","AMZN","APHA","ARKK","BB","BLNK","BNGO","C","CCIV","CCL","CLOV","COST","CRSR","DKNG","EEM","F","FB","FSLY","FSR","FUBO","FXI","G","GDX","GE","GILD","GLD","GM","GME","GO","GOLD","GSAT","GTT","HUGE","HYG","HYLN","IBM","IMO","IPO","IWM","K","KMPH","L","LAZR","LI","LMND","MARA","MO","MSFT","MU","MVIS","NIO","NOK","NVDA","OCGN","PINS","PLTR","PLUG","PSTH","PTON","QQQ","R","RIOT","RKT","RSI","SE","SENS","SI","SKT","SLV","SNAP","SNDL","SOS","SOXL","SPCE","SPY","SQ","SQQQ","T","TD","TGT","TLRY","TLT","TSLA","TWTR","XOM","ZM"]

BRAD_LIST = ["ABBV","GILD","GME","IBM", "MO", "T", "XOM"]
PANI_LIST = ['AAPL','BIGC','BZUN','GRWG','APHA','AMC','LAC','SNOW','PGNY']
WTF_LIST = ['MELI','TSLA','UWMC','RKT','SNDL','LBRDK','IAC','PLTR','BB','CVNA','GME','SKT','AMC','SPY','UPST']
ORACLE = ['GME','AMC','PLTR','TSLA','SE','MELI','TWTR','IAC']


def run_caching():
    # for i in SYMBOL_LIST:
    #     range_data_from_symbol(i, 7, 1.15)
    #     time.sleep(5)
    for i in BRAD_LIST:
        range_data_from_symbol(i, 7, 1.15)
        time.sleep(7)
        range_data_from_symbol(i, 14, 1.15)
        time.sleep(6)
        best_call_trades(i, 7)
        time.sleep(5)
        best_call_trades(i, 14)
    for i in PANI_LIST:
        range_data_from_symbol(i, 7, 1.15)
        time.sleep(7)
        prob_move_pct(i, 7,10)
    for i in WTF_LIST:
        amt_to_invest(i, 7)
        time.sleep(9)
        prob_move_pct(i, 7,10)
    for i in ORACLE:
        range_data_from_symbol(i, 7, 1.15)
        time.sleep(6)
        amt_to_invest(i, 7)



while True:
    check_is_trading()
    d1 = datetime.now()
    curr_date = str(date.today())
    open_time = d1.replace(hour=9)
    open_time = open_time.replace(minute=30)
    close_time = d1.replace(hour=16)
    close_time = close_time.replace(minute=30)
    if r.hget(curr_date,"trading_date") == "yes":
        run_caching()
        r.hset(curr_date,"cache_exists","yes")
    elif not r.hget(curr_date,"cache_exists"):
        run_caching()
        r.hset(curr_date,"cache_exists","yes")
    time.sleep(CACHE_TIMEOUT)
