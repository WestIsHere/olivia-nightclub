FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OLIVIA_HOST=0.0.0.0 \
    OLIVIA_DB=/app/data/olivia.db

WORKDIR /app

COPY olivia-nightclub/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY olivia-nightclub/ .
RUN mkdir -p /app/data

EXPOSE 10000

CMD ["python", "run.py"]
