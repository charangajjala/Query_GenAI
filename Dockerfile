FROM python:3.11-slim

RUN pip install poetry==1.6.1

WORKDIR /code

COPY . /app   

COPY ./package[s] /app/packages

WORKDIR /app

RUN pip install --no-cache-dir --upgrade -r requirements.txt

RUN poetry install --no-interaction --no-ansi

EXPOSE 8000

CMD exec uvicorn quality_agent.main:app --host 0.0.0.0 --port 8000