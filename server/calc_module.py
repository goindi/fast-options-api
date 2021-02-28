import sys
import math
from datetime import datetime, timedelta
from wallstreet import Call, Put, Stock
from scipy import stats
import yfinance as yf
import trading_calendars as tc
import pandas as pd
from scipy.stats import norm
import ast
CACHE_TIMEOUT = 120


import redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def get_expiries_bracket(symbol, num_of_days):
    c = Call(symbol)
    expiries = c.expirations
    curr_date = str(datetime.date(datetime.now()))
    longer_expiry = expiries[-1]
    shorter_expiry = expiries[0]
    shorter_day_bound = (datetime.strptime(shorter_expiry,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
    longer_day_bound = (datetime.strptime(longer_expiry,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
    for i in expiries:
        days_to_exp = abs(datetime.strptime(i,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
        if days_to_exp < num_of_days and days_to_exp > shorter_day_bound  :
            shorter_day_bound = days_to_exp
            shorter_expiry = i
            longer_day_bound = days_to_exp
            longer_expiry = i
        elif days_to_exp >= num_of_days:
            longer_day_bound = days_to_exp
            longer_expiry = i
            break
    shorter_weight = 1;
    if longer_day_bound != shorter_day_bound:
        shorter_weight = (longer_day_bound - num_of_days) / (longer_day_bound - shorter_day_bound)
    return {'shorter_expiry':shorter_expiry,'longer_expiry':longer_expiry,'shorter_day_bound':shorter_day_bound,'longer_day_bound':longer_day_bound, 'shorter_weight':shorter_weight}

def get_strike_bracket(strikes, price_target):
    #strikes = call_object.strikes
    higher_strike = strikes[0]
    lower_strike = strikes[0]
    if price_target < strikes[0]:
        return (-1,-1)
    if price_target > strikes[-1]:
        return (-10,-10)
    for i in strikes:
        if i < price_target and i > lower_strike:
            lower_strike = i
            higher_strike = i
        elif i >= price_target:
            higher_strike = i
            break;
    lower_weight = 1
    if higher_strike != lower_strike:
        lower_weight = (higher_strike - price_target)/(higher_strike - lower_strike)
    return {'lower_strike':lower_strike,'higher_strike':higher_strike, 'lower_weight':lower_weight}

def get_delta(symbol:str, percent_move:float, expiry:str):
    s = Stock(symbol)
    up_px = s.price*(1+percent_move/100)
    down_px = s.price*(1-percent_move/100)
    call = Call(symbol,d=int(expiry[0:2]),m=int(expiry[3:5]),y=int(expiry[6:10]))
    up_delta_dict = get_strike_bracket(call.strikes, up_px)
    call.set_strike(up_delta_dict['lower_strike'])
    delta1 = call.delta()*up_delta_dict['lower_weight']
    call.set_strike(up_delta_dict['higher_strike'])
    delta2 = call.delta()*(1-up_delta_dict['lower_weight'])
    delta_up_move = delta1 + delta2

    put = Put(symbol,d=int(expiry[0:2]),m=int(expiry[3:5]),y=int(expiry[6:10]))
    down_delta_dict = get_strike_bracket(put.strikes, down_px)
    put.set_strike(down_delta_dict['lower_strike'])
    delta1 = -put.delta()*down_delta_dict['lower_weight']
    put.set_strike(down_delta_dict['higher_strike'])
    delta2 = -put.delta()*(1-down_delta_dict['lower_weight'])
    delta_down_move = delta1 + delta2
    return {'delta_up':delta_up_move,'delta_down':delta_down_move}

def get_nd2(symbol:str, percent_move:float, expiry:str):
    y = yf.Ticker(symbol)
    info = y.info
    price = (info['bid']+info['ask'])/2
    up_px = price*(1+percent_move/100)
    down_px = price*(1-percent_move/100)
    expiry = f'{expiry[6:10]}-{expiry[3:5]}-{expiry[0:2]}'
    o = y.option_chain(date='2021-03-12')
    up_delta_dict = get_strike_bracket(o.calls.strike.tolist(), up_px)
    x = o.calls
    x['q'] = info['dividendYield']
    x['r']=0.001
    x['t'] = 8/365
    x['s'] = price
    x['d1']= (np.log(x.s/x.strike)+x.t*(x.r-x.q+x.impliedVolatility*x.impliedVolatility/2))/(x.impliedVolatility*np.sqrt(x.t))
    #x['nd1'] = norm.cdf(x.d1)
    x['d2'] = x.d1-x.impliedVolatility*np.sqrt(x.t)
    x['nd2'] = norm.cdf(x.d2)



    #call.set_strike(up_delta_dict['lower_strike'])
    delta1 = (x.loc[x['strike'] == up_delta_dict['lower_strike']]['nd2'])*up_delta_dict['lower_weight']
    #call.set_strike(up_delta_dict['higher_strike'])
    delta2 = (x.loc[x['strike'] == up_delta_dict['higher_strike']]['nd2'])*(1-up_delta_dict['lower_weight'])
    #delta2 = call.delta()*(1-up_delta_dict['lower_weight'])
    delta_up_move = delta1 + delta2

    #put = Put(symbol,d=int(expiry[0:2]),m=int(expiry[3:5]),y=int(expiry[6:10]))
    down_delta_dict = get_strike_bracket(o.puts.strike.tolist(), down_px)

    y = o.puts
    y['q'] = info['dividendYield']
    y['r']=0.001
    y['t'] = 8/365
    y['s'] = price
    y['d1']= (np.log(y.s/y.strike)+y.t*(y.r-y.q+y.impliedVolatility*y.impliedVolatility/2))/(y.impliedVolatility*np.sqrt(y.t))
    #x['nd1'] = norm.cdf(x.d1)
    y['d2'] = y.d1-y.impliedVolatility*np.sqrt(y.t)
    y['nd2'] = norm.cdf(y.d2)
    #put.set_strike(down_delta_dict['lower_strike'])
    #delta1 = -put.delta()*down_delta_dict['lower_weight']
    delta1 = (y.loc[y['strike'] == down_delta_dict['lower_strike']]['nd2'])*down_delta_dict['lower_weight']

    #put.set_strike(down_delta_dict['higher_strike'])
    #delta2 = -put.delta()*(1-down_delta_dict['lower_weight'])
    delta2 = (y.loc[y['strike'] == down_delta_dict['higher_strike']]['nd2'])*(1-down_delta_dict['lower_weight'])
    delta_down_move = delta1 + delta2
    return {'delta_up':delta_up_move,'delta_down':delta_down_move}

def get_atm_ivol(s, ndays=30):
    #Need to fix for divs, borrow etc to find atm
    symbol = s.ticker
    expiry_dict = get_expiries_bracket(symbol, ndays)
    #First Shorter One
    x = expiry_dict['shorter_expiry']
    shorter_call = Call(symbol,d=int(x[0:2]),m=int(x[3:5]),y=int(x[6:10]))
    strike_dict = get_strike_bracket(shorter_call.strikes, s.price)
    shorter_call.set_strike(strike_dict['lower_strike'])
    lower_vol = shorter_call.implied_volatility()
    shorter_call.set_strike(strike_dict['higher_strike'])
    higher_vol = shorter_call.implied_volatility()
    shorter_ivol = lower_vol*strike_dict['lower_weight'] + higher_vol*(1-strike_dict['lower_weight'])
    #Now longer One
    x = expiry_dict['longer_expiry']
    longer_call = Call(symbol,d=int(x[0:2]),m=int(x[3:5]),y=int(x[6:10]))
    strike_dict = get_strike_bracket(longer_call.strikes, s.price)
    longer_call.set_strike(strike_dict['lower_strike'])
    lower_vol = longer_call.implied_volatility()
    longer_call.set_strike(strike_dict['higher_strike'])
    higher_vol = longer_call.implied_volatility()
    longer_ivol = lower_vol*strike_dict['lower_weight'] + higher_vol*(1-strike_dict['lower_weight'])
    implied_ivol = shorter_ivol*expiry_dict['shorter_weight'] + longer_ivol*(1-expiry_dict['shorter_weight'])
    one_sigma_move_ndays_day = implied_ivol*math.sqrt(ndays/365)
    return (implied_ivol, one_sigma_move_ndays_day)

def range_data_from_symbol(symbol, ndays=7, sigma=1.15):
    symbol = symbol.lower()
    return_dict = {"symbol": "Error",
                    "desc": "No Data found for %s"%symbol
                }
    try:
        if r.hget(f'{symbol}|range|{ndays}|{sigma}','time') and (int(datetime.utcnow().strftime('%s')) - int(r.hget(f'{symbol}|range|{ndays}|{sigma}','time'))) < CACHE_TIMEOUT:
            return ast.literal_eval(r.hget(f'{symbol}|range|{ndays}|{sigma}','value'))
        r.hset(f'{symbol}|range|{ndays}|{sigma}','time',datetime.utcnow().strftime('%s'))
        s = Stock(symbol)
        my_tuple = get_atm_ivol(s, ndays)
        volume = stock_volume(symbol, ndays)
        prob = prob_move_pct(symbol, ndays,0)
        return_dict["symbol"] = symbol
        return_dict["desc"] = s.name
        return_dict["price"] = s.price
        return_dict["ivol"] = my_tuple[0]
        return_dict["low_range"] = s.price - s.price*my_tuple[1]*sigma
        return_dict["high_range"] = s.price + s.price*my_tuple[1]*sigma
        return_dict["volume_pct"] = volume["percentile"]
        return_dict["today_volume"] = volume["volume"]
        return_dict["avg_10d_volume"] = volume["avg_10d_volume"]
        return_dict["prob_up"] = prob["prob_up"]
        r.hset(f'{symbol}|range|{ndays}|{sigma}','time',datetime.utcnow().strftime('%s'))
        r.hset(f'{symbol}|range|{ndays}|{sigma}','value',str(return_dict))
        return return_dict

    except:
        return return_dict

def calculate_bollingers(s, ndays = 20, sigma = 2):
    #Need to update it intraday. Pushing the problem out for later
    #tp is Typical Price. A way to capture high and low (volatility)
    days_back=(ndays*2+10)/0.7 #need trading  days so 0.7
    df = s.historical(days_back=days_back, frequency='d')
    df['typical_price'] = (x['High']+x['Low']+x['Close'])/3
    df['SMA_close'] =  x['Adj Close'].rolling(window=ndays).mean()
    df['SMA_tp'] =  x['typical_price'].rolling(window=ndays).mean()
    df['std_close'] = x['Adj Close'].rolling(window=ndays).std()
    df['std_tp'] = x['typical_price'].rolling(window=ndays).std()
    df['bol_up_close'] = df['SMA_close'] + sigma*df['std_close']
    df['bol_down_close'] = df['SMA_close'] - sigma*df['std_close']
    df['bol_up_tp'] = df['SMA_tp'] + sigma*df['std_tp']
    df['bol_down_tp'] = df['SMA_tp'] - sigma*df['std_tp']

def kelly_fraction(win_prob : float, win_loss_ratio:float)->float:
    return win_prob - (1-win_prob)/win_loss_ratio

def best_call_trades(symbol, num_of_days):
    symbol=symbol.lower()
    if r.hget(f'{symbol}|calltrade|{num_of_days}','time') and (int(datetime.utcnow().strftime('%s')) - int(r.hget(f'{symbol}|calltrade|{num_of_days}','time'))) < CACHE_TIMEOUT:
        return ast.literal_eval(r.hget(f'{symbol}|calltrade|{num_of_days}','value'))
    c = Call(symbol)
    range_dict = range_data_from_symbol(symbol, num_of_days)
    curr_date = str(datetime.date(datetime.now()))
    expiries = c.expirations
    expiry_to_use = expiries[0]
    for i in expiries:
        days_to_exp = abs(datetime.strptime(i,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
        expiry_to_use = i
        if days_to_exp >= num_of_days:
            break
    c = Call(symbol,d=int(expiry_to_use[0:2]),m=int(expiry_to_use[3:5]),y=int(expiry_to_use[6:10]))
    counter = 0
    spread_list = []
    strikes = c.strikes
    for i in strikes:
        if i >= range_dict["high_range"] and counter < 15:
            counter = counter+1
            c.set_strike(i)
            spread_list.append({'strike':i,'bid':c.bid,'ask':c.ask,'delta':c.delta()})
    max_amt = 0
    max_call_amt = 0
    best_spread = {}
    best_call_written = {}

    for i in spread_list:
        #for call
        prob_winning_call = 1 - i['delta'] # Not expiring in the money
        premium_call = i['bid']
        call_win_amt = premium_call*prob_winning_call
        if call_win_amt > max_call_amt:
            max_call_amt = call_win_amt
            best_call_written = i
        for j in spread_list:
            if i['strike'] < j['strike']:
                #for spread
                premium_per_dollar = (i['bid']-j['ask'])/(j['strike']-i['strike'])
                prob_winning_spread = 1 - j['delta']
                win_amt = premium_per_dollar*prob_winning_spread
                if win_amt > max_amt:
                    max_amt = win_amt
                    best_spread = {'strike_to_sell':i['strike'],'strike_to_buy':j['strike'], 'premium_received':i['bid'], 'premium_paid':j['ask'], 'expiry':expiry_to_use}
    best_call_written['expiry'] = expiry_to_use
    return_dict = {'best_spread':best_spread,'best_call':best_call_written}
    r.hset(f'{symbol}|calltrade|{num_of_days}','time',datetime.utcnow().strftime('%s'))
    r.hset(f'{symbol}|calltrade|{num_of_days}','value',str(return_dict))
    return return_dict

def prob_move_pct(symbol:str, n_days:int, percent:float):
    symbol=symbol.lower()
    if r.hget(f'{symbol}|pmovepct|{n_days}|{percent}','time') and (int(datetime.utcnow().strftime('%s')) - int(r.hget(f'{symbol}|pmovepct|{n_days}|{percent}','time'))) < CACHE_TIMEOUT:
        return ast.literal_eval(r.hget(f'{symbol}|pmovepct|{n_days}|{percent}','value'))
    c = Call(symbol)
    curr_date = str(datetime.date(datetime.now()))
    expiries = c.expirations
    expiry_to_use = expiries[0]
    for i in expiries:
        days_to_exp = abs(datetime.strptime(i,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
        expiry_to_use = i
        if days_to_exp >= n_days:
            break
    my_delta = get_delta(symbol, percent, expiry_to_use)
    return_dict = {"move_percent":percent, 'expiry':expiry_to_use, "prob_down":my_delta['delta_down'],"prob_up":my_delta['delta_up'] }
    r.hset(f'{symbol}|pmovepct|{n_days}|{percent}','time',datetime.utcnow().strftime('%s'))
    r.hset(f'{symbol}|pmovepct|{n_days}|{percent}','value',str(return_dict))
    return return_dict


def prob_move_sigma(symbol:str, n_days:int, sigma_fraction_to_use:float):
    c = Call(symbol)
    curr_date = str(datetime.date(datetime.now()))
    expiries = c.expirations
    expiry_to_use = expiries[0]
    my_n_days = 0
    for i in expiries:
        days_to_exp = abs(datetime.strptime(i,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
        expiry_to_use = i
        my_n_days = days_to_exp
        if days_to_exp >= n_days:
            break
    my_tuple = get_atm_ivol(Stock(symbol), my_n_days)
    my_percent = my_tuple[1]*100*sigma_fraction_to_use
    my_delta = get_delta(symbol, my_percent, expiry_to_use)
    prob_down = my_delta['delta_down']
    prob_up = my_delta['delta_up']
    norm_prob_down = 0
    norm_prob_up = 0
    if prob_up > prob_down:
        norm_prob_down = 0.5
        norm_prob_up = prob_up*0.5/prob_down
    else:
        norm_prob_up = 0.5
        norm_prob_down = prob_down*0.5/prob_up
    return {"move_percent":my_percent, 'expiry':expiry_to_use, "prob_down":prob_down,"norm_prob_down":norm_prob_down,"prob_up":prob_up, "norm_prob_up":norm_prob_up}

def implied_forward(symbol, n_days):
    s = Stock(symbol)
    c = Call(symbol)
    curr_date = str(datetime.date(datetime.now()))
    expiries = c.expirations
    expiry_to_use = expiries[0]
    my_n_days = 0
    for i in expiries:
        days_to_exp = abs(datetime.strptime(i,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
        expiry_to_use = i
        my_n_days = days_to_exp
        if days_to_exp >= n_days:
            break
    call = Call(symbol,d=int(expiry_to_use[0:2]),m=int(expiry_to_use[3:5]),y=int(expiry_to_use[6:10]))
    put = Put(symbol,d=int(expiry_to_use[0:2]),m=int(expiry_to_use[3:5]),y=int(expiry_to_use[6:10]))
    bracket_dict = get_strike_bracket(call.strikes, s.price)
    forward = s.price
    if bracket_dict['lower_weight'] > 0.5:
        call.set_strike(bracket_dict['lower_strike'])
        put.set_strike(bracket_dict['lower_strike'])
        forward = bracket_dict['lower_strike'] - put.price + call.price
    else:
        call.set_strike(bracket_dict['higher_strike'])
        put.set_strike(bracket_dict['higher_strike'])
        forward = bracket_dict['higher_strike'] - put.price + call.price
    return {"forward_price":forward,"current_price":s.price, "expiry":expiry_to_use}

def best_put_trades(symbol, num_of_days):
    symbol=symbol.lower()
    if r.hget(f'{symbol}|puttrade|{num_of_days}','time') and (int(datetime.utcnow().strftime('%s')) - int(r.hget(f'{symbol}|puttrade|{num_of_days}','time'))) < CACHE_TIMEOUT:
        return ast.literal_eval(r.hget(f'{symbol}|puttrade|{num_of_days}','value'))

    p = Put(symbol)
    range_dict = range_data_from_symbol(symbol, num_of_days)
    curr_date = str(datetime.date(datetime.now()))
    expiries = p.expirations
    expiry_to_use = expiries[0]
    for i in expiries:
        days_to_exp = abs(datetime.strptime(i,'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
        expiry_to_use = i
        if days_to_exp >= num_of_days:
            break
    p = Put(symbol,d=int(expiry_to_use[0:2]),m=int(expiry_to_use[3:5]),y=int(expiry_to_use[6:10]))
    counter = 0
    spread_list = []
    strikes = p.strikes
    for i in strikes:
        if i <= range_dict["high_range"] and counter < 15:
            counter = counter+1
            p.set_strike(i)
            spread_list.append({'strike':i,'bid':p.bid,'ask':p.ask,'delta':-p.delta()})
    max_amt = 0
    max_put_amt = 0
    best_spread = {}
    best_put_written = {}
    spread_list.reverse()
    for i in spread_list:
        #for call
        prob_winning_put = 1 - i['delta']
        premium_put = i['bid']
        put_win_amt = premium_put*prob_winning_put
        if put_win_amt > max_put_amt:
            max_put_amt = put_win_amt
            best_put_written = i
        for j in spread_list:
            if i['strike'] > j['strike']:
                #for spread
                premium_per_dollar = (i['bid']-j['ask'])/abs(j['strike']-i['strike'])
                prob_winning_spread = 1 - j['delta']
                win_amt = premium_per_dollar*prob_winning_spread
                if win_amt > max_amt:
                    max_amt = win_amt
                    best_spread = {'strike_long':i['strike'],'strike_short':j['strike'], 'premium_received':i['bid'], 'premium_paid':j['ask'], 'expiry':expiry_to_use}
    best_put_written['expiry'] = expiry_to_use
    return_dict = {'best_spread':best_spread,'best_put':best_put_written}
    r.hset(f'{symbol}|puttrade|{num_of_days}','time',datetime.utcnow().strftime('%s'))
    r.hset(f'{symbol}|puttrade|{num_of_days}','value',str(return_dict))
    return return_dict


def amt_to_invest(symbol:str,n_days:int):
    symbol=symbol.lower()
    if r.hget(f'{symbol}|kelly|{n_days}','time') and (int(datetime.utcnow().strftime('%s')) - int(r.hget(f'{symbol}|kelly|{n_days}','time'))) < CACHE_TIMEOUT:
        return ast.literal_eval(r.hget(f'{symbol}|kelly|{n_days}','value'))
    prob_dict = prob_move_pct(symbol, n_days,0)
    #print(prob_dict)
    curr_date = str(datetime.date(datetime.now()))
    days_to_exp = abs(datetime.strptime(prob_dict['expiry'],'%d-%m-%Y') - datetime.strptime(curr_date,'%Y-%m-%d')).days
    return_dict = {"kelly":2*prob_dict['prob_up'] - 1, "expiry":prob_dict['expiry'], "prob_up":prob_dict['prob_up'], "kelly2":prob_dict['prob_up']-0.5}
    r.hset(f'{symbol}|kelly|{n_days}','time',datetime.utcnow().strftime('%s'))
    r.hset(f'{symbol}|kelly|{n_days}','value',str(return_dict))
    return return_dict

    # my_tuple = get_atm_ivol(Stock(symbol), days_to_exp)
    # perc_move = my_tuple[1]*1.15/2
    # print(f"{perc_move}, {prob_dict['prob_up']},{prob_dict['prob_down']}")
    # return (prob_dict['prob_up'] - prob_dict['prob_down'])/perc_move

def div_details(symbol:str):
    symbol = symbol.upper()
    y = yf.Ticker(symbol)
    if y.dividends.empty:
        div = "0"
        div_date = ""
        div_yld = "0"
    else:
        div = y.dividends[-1]
        div_date = str(y.dividends.index[-1])[0:10]
        div_yld = y.info['dividendYield']
    return {'div':div, 'div_date':div_date, 'div_yld':div_yld}

def stock_volume (symbol:str, n_days:int):
    symbol = symbol.upper()
    curr_date = str(datetime.now().date())
    if not r.get(curr_date):
        xnys = tc.get_calendar("XNYS")
        print("here")
        if xnys.is_session(pd.Timestamp(datetime.now())):
            r.set(curr_date,"trading")
        else:
            r.set(curr_date,"not-trading")
    s = yf.Ticker(symbol)
    weight = 1
    d1 = datetime.now()
    #if d1.hour>9 and d1.hour<16:

    if r.get(curr_date) == "trading":
        print("here2")
        d2 = d1.replace(hour=9)
        d2 = d1.replace(minute=30)
        delta = d1 - d2
        if delta.total_seconds() >= 390*60:
            weight = 1
            r.set(curr_date,"not-trading")
        else:
            weight = (390*60)/delta.total_seconds()

    today_volume = s.info['volume']*weight
    p = stats.percentileofscore(s.history()[-n_days:].Volume,today_volume)
    avg_10d_volume = 0
    if r.hget(symbol,'date') != curr_date or not r.hget(symbol,'avg_10d_volume') :
        r.hset(symbol,'date', curr_date)
        r.hset(symbol,'avg_10d_volume', s.info['averageVolume10days'])
    return {'symbol':symbol, 'percentile':p, 'volume':today_volume, 'avg_10d_volume':int(r.hget(symbol,'avg_10d_volume'))}
