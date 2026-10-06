FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY refresh_cache.py .

RUN useradd --create-home --uid 1000 appuser && chown -R appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1

CMD ["python", "refresh_cache.py"]
