FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

# 明示的なCMD
CMD ["python", "app.py"]

EXPOSE 8080