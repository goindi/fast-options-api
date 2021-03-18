from fastapi import APIRouter, Body
from fastapi.encoders import jsonable_encoder


from datetime import datetime
from server.calc_module import range_data_from_symbol, best_call_trades, best_put_trades, get_gamma_squeeze, get_current_stock_details
from server.calc_module import prob_move_pct, prob_move_sigma, implied_forward, amt_to_invest, div_details, stock_volume, best_put_protection
from server.calc_module import  crypto_range_data_from_symbol
from server.twitter_sentiment import find_twitter_sentiment

tags_metadata = [
    {
        "name": "range",
        "description": "Using options data we calculate at-the-money implied volatility and use that as a proxy for standard deviation(sigma). Default range is the one that give us the 75% probabilty. If you want 90% probability range use sigma=1.96",
        "externalDocs": {
            "description": "Normal Distribution",
            "url": "https://en.wikipedia.org/wiki/Normal_distribution#Standard_deviation_and_coverage",
        },
    },
    {
        "name": "doom",
        "description": "Using options data we calculate the probability of options expiring in the money. For a call that is eqivalent to the probability of stock being over strike and for the put prob of stock being below the strike. Doom gives us the probability of put expiring in the money",
        "externalDocs": {
            "description": "Delta Approximation",
            "url": "https://www.macroption.com/delta-calls-puts-probability-expiring-itm/",
        },
    },
    {
        "name": "volume",
        "description": "Using stock volume from past 10 days, we calculate the current level in two ways - as a multiple of average daily volume and as a percentile. Volume numbers during a trading session are scaled appropriately",
        "externalDocs": {
            "description": "Yahoo Finance",
            "url": "https://finance.yahoo.com/quote/spy",
        },
    },
    {
        "name": "call_trade",
        "description": "Using options data we calculate the probabilty of a call option expiring in the money. That probabilty along with premium received gives us an idea of which option has the maximum payoff potential. Similar methodology is used to find the optimal spread trade",
        "externalDocs": {
            "description": "Yahoo Finance",
            "url": "https://finance.yahoo.com/quote/SPY/options?p=SPY",
        },
    },
    {
        "name": "put_trade",
        "description": "Using options data we calculate the probabilty of a put option expiring in the money. That probabilty along with premium received gives us an idea of which option has the maximum payoff potential. Similar methodology is used to find the optimal spread trade",
        "externalDocs": {
            "description": "Yahoo Finance",
            "url": "https://finance.yahoo.com/quote/SPY/options?p=SPY",
        },
    },
    {
        "name": "kelly",
        "description": "Using at-the-money options data we calculate the options implied probabilty of stock going up.  Based on those probabilty we calculate the optimal betting size of stock using Kelly criterion. ",
        "externalDocs": {
            "description": "Kelly Criterion",
            "url": "https://en.wikipedia.org/wiki/Kelly_criterion",
        },
    },
    {
        "name": "dividend",
        "description": "Shows last dividend date and amount as well as dividend yield. ",
        "externalDocs": {
            "description": "Yahoo Finance",
            "url": "https://finance.yahoo.com/quote/SPY/options?p=SPY",
        },
    },
]

router = APIRouter()

@router.get("/options")
async def get_notes() -> dict:
    return get_range_data_from_symbol('SPY',7)

@router.get("/options/range/{symbol}")
async def get_range_data(symbol: str, days:int = 7, sigma:float = 1.15) -> dict:
    return range_data_from_symbol(symbol,days)

@router.get("/options/yolo/{my_list}")
async def get_my_yolo(my_list: str, days:int = 7, sigma:float = 0.5) -> dict:
    symbol_list = my_list.split(",")
    return_dict = get_best_trade(symbol_list,days,sigma)
    return return_dict
    #return yolo_dict

def get_best_trade(symbol_list: list, days:int, sigma:float ) -> dict:
    yolo_dict = {}
    max_up_prob = 0
    max_up_symbol = ""
    max_down_prob = 0
    max_down_symbol = ""
    up_expiry = ""
    down_expiry = ""

    for i in symbol_list:
        x = prob_move_sigma(i, days, sigma)
        if "error" in x:
            continue
        yolo_dict[i] = x
        if yolo_dict[i]["norm_prob_up"] > max_up_prob:
            max_up_prob = yolo_dict[i]["norm_prob_up"]
            max_up_symbol = i
            up_expiry = yolo_dict[i]["expiry"]
        if yolo_dict[i]["norm_prob_down"] > max_down_prob:
            max_down_prob = yolo_dict[i]["norm_prob_down"]
            max_down_symbol = i
            down_expiry = yolo_dict[i]["expiry"]
    up_kelly = amt_to_invest(max_up_symbol,days)
    down_kelly = amt_to_invest(max_down_symbol,days)
    return {"bullish_stock_symbol":max_up_symbol, "bullish_kelly":up_kelly["kelly"],"bullish_kelly2":up_kelly["kelly2"], "bearish_stock_symbol":max_down_symbol,"bearish_kelly":down_kelly["kelly"],"bullish_stock_details":yolo_dict[max_up_symbol], "bearish_stock":yolo_dict[max_down_symbol]}

@router.get("/options/tradeoftheday/{my_list}")
async def get_my_trade_of_day(my_list: str, days:int = 7, sigma:float = 0.5) -> str:
    symbol_list = my_list.split(",")
    yolo_trade_dict = get_best_trade(symbol_list,days,sigma)
    call_trade =  best_call_trades(yolo_trade_dict['bullish_stock_symbol'], days)
    call_trade = call_trade['best_call']
    print(f"{yolo_trade_dict}--{call_trade}")

    bullet_1 = ""
    symbol = yolo_trade_dict["bullish_stock_symbol"]
    if yolo_trade_dict["bullish_kelly"] > 0:
        #kelly_to_use = min(yolo_trade_dict["bullish_kelly"],0.1)*100
        kelly_to_use = yolo_trade_dict["bullish_kelly2"]*100
        kelly_to_use2 = yolo_trade_dict["bullish_kelly"]*100
        bullet_1 = f'Planning $100 YOLO? Buy ${kelly_to_use:.2f} of {symbol} (or more aggressive )Planning $100 YOLO? Buy ${kelly_to_use2:.2f} of {symbol}'

    expiry = call_trade['expiry']
    exp = datetime.strptime(expiry,'%d-%m-%Y').strftime('%b %d')
    #bullets_of_day = bullets_of_day + "&#13;&#10;"
    bullet_2=f"Have 100+ Shares of {symbol}? Sell {exp}, Covered Call @ ${call_trade['strike']} for {symbol}"
    return f'{bullet_1}           {bullet_2}'

@router.get("/options/call_trades/{symbol}")
async def get_my_call_trades(symbol: str, days:int = 7) -> dict:
    return best_call_trades(symbol, days)

@router.get("/options/put_trades/{symbol}")
async def get_my_put_trades(symbol: str, days:int = 7) -> dict:
    return best_put_trades(symbol, days)
@router.get("/options/put_protection/{symbol}")
async def get_my_put_protection(symbol: str, days:int = 7) -> dict:
    return best_put_protection(symbol, days)

@router.get("/options/prob_pct/{symbol}")
async def get_probability_of_n_pct_move(symbol: str, days:int = 7, percent:float = 5) -> dict:
    return prob_move_pct(symbol, days, percent)

@router.get("/options/prob_sigma/{symbol}")
async def get_probability_of_n_sigma_move(symbol: str, days:int = 7, sigma:float = 0.5) -> dict:
    return prob_move_sigma(symbol, days, sigma)

@router.get("/options/forward/{symbol}")
async def get_option_implied_forward(symbol: str, days:int = 7) -> dict:
    return implied_forward(symbol, days)

@router.get("/options/kelly/{symbol}")
async def get_amt_to_invest(symbol: str, days:int = 7) -> dict:
    return amt_to_invest(symbol, days)

@router.get("/options/doom")
async def get_doom_prob(symbol: str = 'SPY', days:int = 365, percent:int = 20) -> dict:
    return prob_move_pct(symbol, days, percent)

@router.get("/options/doom/{symbol}")
async def get_doom_prob(symbol: str, days:int = 365, percent:int = 20) -> dict:
    return prob_move_pct(symbol, days, percent)

@router.get("/options/gamma/{symbol}")
async def get_doom_prob(symbol: str, days:int = 7) -> dict:
    return get_gamma_squeeze(symbol, days)

@router.get("/stocks/volume/{symbol}")
async def get_stock_volume(symbol: str, days:int = 10) -> dict:
    return stock_volume(symbol, days)

@router.get("/stocks/dividend/{symbol}")
async def get_div_details(symbol: str) -> dict:
    return div_details(symbol)

@router.get("/stocks/details/{symbol}")
async def get_stock_details(symbol: str) -> dict:
    return get_current_stock_details(symbol)

@router.get("/sentiment/twitter/{symbol}")
async def get_twitter_sentiments_details(symbol: str, num_of_tweets:int=10) -> dict:
    return find_twitter_sentiment(symbol,num_of_tweets)

@router.get("/crypto/range/{symbol}")
async def get_range_data(symbol: str, days:int = 7, sigma:float = 1.15) -> dict:
    return crypto_range_data_from_symbol(symbol,days,sigma)
