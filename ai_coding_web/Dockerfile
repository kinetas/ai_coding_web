FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY crawler ./crawler
COPY etl.py .

ENV APP_ENV=production
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "python -m backend.app.init_db && uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
