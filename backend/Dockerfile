FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Seoul
WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 academy

COPY backend/db.py backend/web_app.py backend/main.py ./
COPY backend/web/ ./web/

USER academy
EXPOSE 8000
CMD ["python", "main.py"]
