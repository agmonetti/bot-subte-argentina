FROM python:3.11-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

RUN useradd --create-home --uid 10001 botuser \
    && mkdir -p /app/src/data \
    && chown -R botuser:botuser /app
USER botuser

CMD ["python", "src/main.py"]
