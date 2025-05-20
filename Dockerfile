# Dockerfile
# Используем официальный образ Python
FROM python:3.10-slim-buster

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы приложения
COPY app/ app/

# Открываем порт, на котором будет работать Uvicorn
EXPOSE 8000

# Команда для запуска приложения с помощью Uvicorn
# --host 0.0.0.0 делает приложение доступным извне контейнера
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]