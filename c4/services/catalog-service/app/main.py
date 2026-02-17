from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI(title="catalog-service", version="0.1.0")


@app.get("/health", response_class=PlainTextResponse)
def health():
    return "OK"