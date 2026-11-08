FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system minifabrica && adduser --system --ingroup minifabrica minifabrica

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend
COPY database ./database
COPY scripts ./scripts

RUN mkdir -p /app/data/uploads && chown -R minifabrica:minifabrica /app
USER minifabrica

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
