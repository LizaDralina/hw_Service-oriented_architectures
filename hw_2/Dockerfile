FROM openapitools/openapi-generator-cli:v7.7.0 AS codegen
WORKDIR /work

COPY src/main/resources/openapi/products.yaml /work/products.yaml

RUN /usr/local/bin/docker-entrypoint.sh generate \
  -g python-fastapi \
  -i /work/products.yaml \
  -o /work/generated \
  --additional-properties=packageName=openapi_server

FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src/ /app/src/
COPY --from=codegen /work/generated /app/generated
COPY src/impl/products_api.py /app/generated/src/openapi_server/apis/products_api.py


ENV PYTHONPATH=/app/src:/app/generated/src

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
