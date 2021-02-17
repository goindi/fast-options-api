from fastapi import APIRouter, Body
from fastapi.encoders import jsonable_encoder
from server.calc_module import get_range_data_from_symbol, get_best_call_trades, get_best_put_trades, get_probability_move, get_normalized_probability_move

router = APIRouter()

@router.get("/")
async def get_notes() -> dict:
    return get_range_data_from_symbol('SPY',7)

@router.get("/range/{symbol}")
async def get_range_data(symbol: str, days:int = 7) -> dict:
    return get_range_data_from_symbol(symbol,days)

@router.get("/yolo/{my_list}")
async def get_my_yolo(my_list: str) -> dict:
    symbol_list = my_list.split(",")
    yolo_dict = {}
    max_std = 0
    max_std_symbol = ""
    for i in symbol_list:
        yolo_dict[i] = get_range_data_from_symbol(i,7)
        if yolo_dict[i]["ivol"] > max_std:
            max_std = yolo_dict[i]["ivol"]
            max_std_symbol = i
    return yolo_dict[max_std_symbol]
    #return yolo_dict

@router.get("/call_trades/{symbol}")
async def get_my_call_trades(symbol: str, days:int = 7) -> dict:
    return get_best_call_trades(symbol, days)

@router.get("/put_trades/{symbol}")
async def get_my_put_trades(symbol: str, days:int = 7) -> dict:
    return get_best_put_trades(symbol, days)

@router.get("/prob/{symbol}")
async def get_my_probabilities(symbol: str, days:int = 7, percent:float = 5) -> dict:
    return get_probability_move(symbol, days, percent)

@router.get("/normalized_prob/{symbol}")
async def get_my_normalized_probability_move(symbol: str, days:int = 7, sigma:float = 0.5) -> dict:
    return get_normalized_probability_move(symbol, days, sigma)
