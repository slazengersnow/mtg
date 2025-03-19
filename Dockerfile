FROM python:3.9-slim

WORKDIR /app

# 依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# 環境変数を設定
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# コンテナ起動時に実行するコマンド
CMD ["python", "app.py"]

# ポートを公開
EXPOSE 8080