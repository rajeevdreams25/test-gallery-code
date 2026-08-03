FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Mounted as volumes in docker-compose so uploads and the DB survive rebuilds.
RUN mkdir -p /app/uploads /app/data

ENV DATABASE_URL=sqlite:////app/data/gallery.db \
    UPLOAD_DIR=/app/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
