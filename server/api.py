from fastapi import FastAPI
from server.routes import router as OptionRouter
app = FastAPI()

@app.get("/", tags=["Root"])
async def read_root():
  return {
    "message": "Welcome to API for Apes. Use the /docs route to proceed"
   }
app.include_router(OptionRouter)
