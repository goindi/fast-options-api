from fastapi import FastAPI
from server.routes import router as OptionRouter
app = FastAPI()

@app.get("/", tags=["Root"])
async def read_root():
  return {
    "message": "Welcome to my notes application, use the /docs route to proceed"
   }
app.include_router(OptionRouter, prefix="/options")
