from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from server.routes import router as OptionRouter
from server.routes import tags_metadata

import logging.config
from fastapi_route_logger_middleware import RouteLoggerMiddleware

app = FastAPI(openapi_tags=tags_metadata)
logging.config.fileConfig("./logging.conf")
app.add_middleware(RouteLoggerMiddleware)
origins = [
        "http://localhost.tiangolo.com",
        "https://localhost.tiangolo.com",
        "http://localhost",
        "http://localhost:8080",
          ]

app.add_middleware(
         CORSMiddleware,
         allow_origins=["*"],
         allow_credentials=True,
         allow_methods=["*"],
         allow_headers=["*"],
         )

@app.get("/", tags=["Root"])
async def read_root():
  return {
    "message": "Welcome to API for Apes. Use the /docs route to proceed"
   }
app.include_router(OptionRouter)
