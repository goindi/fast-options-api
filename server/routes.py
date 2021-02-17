from fastapi import APIRouter, Body
from fastapi.encoders import jsonable_encoder
from server.calc_module import get_range_data_from_symbol, get_best_call_spread

router = APIRouter()

@router.get("/")
async def get_notes() -> dict:
    return get_range_data_from_symbol('SPY',7)

@router.get("/range/{symbol}->dict")
async def get_range_data(symbol: str) -> dict:
    return get_range_data_from_symbol(symbol,7)

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

@router.get("/call_spread/{symbol}")
async def get_my_call_spread(symbol: str) -> dict:
    return get_best_call_spread(symbol, 7)
