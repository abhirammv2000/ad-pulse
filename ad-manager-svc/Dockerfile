FROM python:3.12-slim

WORKDIR /app

# Dependencies first, so edits to the source don't invalidate the install layer.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as a non-root user.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser /app
USER appuser

EXPOSE 5000

# gunicorn, not the Flask development server: `flask run` is single-threaded
# and explicitly not for production use. --preload imports the app once in
# the master before forking workers, so create_app()'s schema bootstrap
# (config/db.py:init_db) runs once instead of racing across 4 workers.
CMD ["gunicorn", "--preload", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "60", "run:app"]
