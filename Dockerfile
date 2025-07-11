# 1) Базовый образ
FROM python:3.10-slim

# 2) Системные пакеты для psycopg2
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# 3) Рабочая директория
WORKDIR /app

# 4) Переменные окружения
ENV PYTHONUNBUFFERED=1

# 5) Копируем и ставим зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# 6) Копируем весь код
COPY . .

# 7) Экспонируем порт
EXPOSE 8001

# 8) Точка входа
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
