# syntax=docker/dockerfile:1
# 專案根目錄作為 build context；保留原本目錄結構，推論不依賴 Windows 路徑。
FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# XGBoost CPU 需要 OpenMP。CA mount 只供雲端代理建置，部署主機可省略。
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then cp /run/secrets/proxy_ca /usr/local/share/ca-certificates/build-proxy.crt; update-ca-certificates; fi; \
    apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* /usr/local/share/ca-certificates/build-proxy.crt \
    && update-ca-certificates
COPY sentinel/model/requirements.txt /app/sentinel/model/requirements.txt
COPY sentinel/gateway/requirements.txt /app/sentinel/gateway/requirements.txt
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install -r /app/sentinel/gateway/requirements.txt

# 僅放推論程式、選用清單及已訓練套件；不複製資料集、私人 .env 或測試紀錄。
COPY sentinel/model/predict.py sentinel/model/features.py sentinel/model/request_input.py /app/sentinel/model/
COPY sentinel/gateway/app.py sentinel/gateway/docker_start.py /app/sentinel/gateway/
COPY sentinel/gateway/model/ /app/sentinel/gateway/model/
COPY sentinel/analysis/api-extension/medusa-holdout-inventory.json /app/sentinel/analysis/api-extension/
# Git checkout 的本機檔案權限可能很嚴格，映像中明確賦予非 root 使用者讀取權。
RUN chmod -R a+rX /app
USER 10001:10001
EXPOSE 8080
CMD ["python", "/app/sentinel/gateway/docker_start.py"]
