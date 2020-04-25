FROM python:3.8-alpine AS build

COPY requirements.txt .

RUN pip install -U -r requirements.txt

FROM python:3.8-alpine

COPY --from=build /usr/local/lib/python3.8/site-packages /usr/local/lib/python3.8/site-packages

RUN mkdir /app

WORKDIR /app

COPY sync_hosts.py .

ENTRYPOINT ["python", "sync_hosts.py"]
