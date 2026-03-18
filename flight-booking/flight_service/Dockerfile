FROM python:3.12-slim

WORKDIR /service

COPY flight_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY proto ./proto
RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=. \
    --grpc_python_out=. \
    ./proto/flight_service.proto

COPY flight_service/app ./app

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "app.server"]
