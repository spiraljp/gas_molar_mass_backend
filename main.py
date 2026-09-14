from fastapi import FastAPI
import uvicorn
from api.handlers import router
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Gas Catalog App")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI Web Application!"}

if __name__ == "__main__":
    # Запуск сервера. reload=True автоматически перезапускает сервер при изменении кода
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
