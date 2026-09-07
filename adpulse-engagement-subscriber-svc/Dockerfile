FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 appuser && chown -R appuser /app
USER appuser

# Unbuffered so the subscriber's log lines reach kubectl logs promptly.
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
