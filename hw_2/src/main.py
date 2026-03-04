from fastapi import FastAPI

from openapi_server.apis.products_api import router as products_router

app = FastAPI()
app.include_router(products_router)