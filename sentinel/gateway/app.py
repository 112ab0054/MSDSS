"""Medusa 閘道原型：分析請求但不攔截，原始請求仍轉送後端。

啟動：uvicorn app:app --host 127.0.0.1 --port 8080
設定：MEDUSA_UPSTREAM、GATEWAY_MODEL_DIR（可省略，省略時僅做轉送）。
本版為開發骨架：大型串流、WebSocket、檔案上傳的特徵分析尚未完成。
"""
import asyncio
from contextlib import asynccontextmanager
import json
import logging
import os
from pathlib import Path
import sys
from urllib.parse import parse_qs

import httpx
from fastapi import FastAPI, Request
from starlette.responses import Response

# 由程式位置定位模型模組，不依賴使用者從哪個目錄啟動。
MODEL_CODE = Path(__file__).resolve().parents[1] / "model"
sys.path.insert(0, str(MODEL_CODE))
log = logging.getLogger("gateway")

# 這些是逐段連線標頭，代理須重新建立，不能直接複製到下一段連線。
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
       "te", "trailer", "transfer-encoding", "upgrade"}


def forwarded_headers(headers):
    """保留重複 header，同時排除 Connection 指定的逐段標頭。"""
    connection = {part.strip().lower() for key, value in headers
                  if key.lower() == b"connection" for part in value.decode("latin-1").split(",")}
    blocked = HOP | connection
    return [(key, value) for key, value in headers if key.decode("latin-1").lower() not in blocked]


def model_request(request, body):
    """模型使用解析後副本；轉送時使用原始 bytes，不能把遮蔽值送給後端。

    query 使用清單保留重複參數。一般 header 保留，同名值以逗號合併供現有
    特徵程式使用；實際轉送仍保留重複項。敏感值在模型副本中遮蔽。
    JSON/form 支援欄位解析；其他格式只記錄格式，不分析檔案／二進位內容。
    """
    from features import SENSITIVE, clean
    headers = {}
    for key, value in request.headers.raw:
        name, value = key.decode("latin-1").lower(), value.decode("latin-1")
        value = "[REDACTED]" if SENSITIVE.search(name) else value
        headers[name] = headers[name] + ", " + value if name in headers else value
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    parsed = None
    if body:
        text = body.decode("utf-8", errors="replace")
        if content_type == "application/json" or content_type.endswith("+json"):
            try:
                parsed = clean(json.loads(text))
            except ValueError:
                parsed = text  # 畸形 JSON 也可能包含攻擊訊號，不默默當作空白。
        elif content_type == "application/x-www-form-urlencoded":
            parsed = clean(parse_qs(text, keep_blank_values=True))
        else:
            parsed = {"unsupported_content_type": content_type, "body_bytes": len(body)}
    return {"method": request.method, "path": request.url.path,
            "query": clean(parse_qs(request.url.query, keep_blank_values=True)),
            "headers": headers, "body": parsed}


@asynccontextmanager
async def lifespan(app):
    """共用 HTTP 連線池；模型只載入一次，不在每個請求重新讀檔。"""
    upstream = os.environ.get("MEDUSA_UPSTREAM", "http://127.0.0.1:9000").rstrip("/")
    if not upstream.startswith(("http://", "https://")):
        raise ValueError("MEDUSA_UPSTREAM 必須是 HTTP(S) 網址")
    app.state.upstream = upstream
    app.state.predictor = None
    model_dir = os.environ.get("GATEWAY_MODEL_DIR")
    if model_dir:
        try:
            from predict import Predictor
            app.state.predictor = Predictor(Path(model_dir))
        except Exception as error:
            # 只記錯誤類型，不記錄 Token、body 或可能包含敏感資訊的錯誤內容。
            log.warning("model_load_failed type=%s", type(error).__name__)
    else:
        log.warning("model_disabled: GATEWAY_MODEL_DIR 未設定，僅轉送")
    app.state.model_lock = asyncio.Lock()
    async with httpx.AsyncClient(timeout=30, follow_redirects=False, trust_env=False) as client:
        app.state.client = client
        yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy(request: Request, path: str):
    # 本版讀取整個本文；正式使用前須增加大小限制及串流支援。
    body = await request.body()
    predictor = request.app.state.predictor
    if predictor is not None:
        try:
            # 模型運算放到執行緒，避免直接阻塞事件迴圈；鎖避免同物件並行問題。
            # 目前沒有硬性推論逾時，正式整合應改成獨立 worker 與有界佇列。
            async with request.app.state.model_lock:
                result = await asyncio.to_thread(predictor.predict, model_request(request, body))
            log.info("prediction label=%s exploratory=%s", result["label"], result["exploratory"])
        except Exception as error:
            log.warning("prediction_failed type=%s", type(error).__name__)
            # 分析失敗照常轉送；這是只告警模式，不是安全封鎖策略。
    # 使用原始路徑與 query，避免重新編碼改變 %2F、重複參數等內容。
    raw_path = request.scope.get("raw_path", request.url.path.encode()).decode("ascii")
    query = request.scope["query_string"].decode("ascii")
    target = request.app.state.upstream + raw_path + ("?" + query if query else "")
    headers = [(k, v) for k, v in forwarded_headers(request.headers.raw)
               if k.lower() not in {b"host", b"content-length"}]
    try:
        # Host/Content-Length 交由 HTTP client 依上游位址與原始本文重新建立。
        upstream_request = request.app.state.client.build_request(request.method, target, headers=headers, content=body)
        upstream = await request.app.state.client.send(upstream_request, stream=True)
        try:
            # 使用 raw bytes，避免自動解壓後仍保留 Content-Encoding 導致瀏覽器解讀錯誤。
            content = b"".join([chunk async for chunk in upstream.aiter_raw()])
            response = Response(content, status_code=upstream.status_code)
            response.raw_headers = forwarded_headers(upstream.headers.raw)
            return response
        finally:
            await upstream.aclose()
    except httpx.TimeoutException:
        return Response("Upstream timeout", status_code=504)
    except httpx.HTTPError:
        return Response("Upstream unavailable", status_code=502)
