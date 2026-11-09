"""Medusa 閘道原型：分析請求但不攔截，原始請求仍轉送後端。

啟動：uvicorn app:app --host 127.0.0.1 --port 8080
設定：MEDUSA_UPSTREAM、GATEWAY_MODEL_DIR（可省略，省略時僅做轉送）。
資料流程：瀏覽器 → 本閘道 → 建立遮蔽後的模型副本 → XGBoost 預測 → 原請求轉送 Medusa。
回程則把 Medusa 的狀態碼、可轉送 header 與回應本文交還瀏覽器。

目前無論預測 normal、sqli 或 xss 都照常轉送，模型失敗也照常轉送。
此設計減少誤判直接擋住 demo 操作的風險，但推論仍會增加等待時間，
也不保證後端不受攻擊、不當請求或服務故障影響。
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
    """保留重複 header，同時排除 Connection 指定的逐段標頭。

    輸入 headers：原始 (名稱 bytes, 值 bytes) 的成對清單，不是一般字典。
    輸出同樣型別的清單，移除不能跨代理連線複製的 header，其他值保持原樣。
    例如 Connection: keep-alive, X-Temp 會使 Connection、Keep-Alive、X-Temp 被排除。
    多個 Set-Cookie 仍各自保留，不能因轉成字典而只剩最後一個。

    Connection/HOP 屬於連線這一段的設定，瀏覽器到 gateway 與 gateway 到後端是兩段連線。
    Host/Content-Length 不在這個函式統一刪除；請求端由 proxy 額外移除後再交 HTTPX 重建。
    不在這裡刪 Authorization/Cookie，否則後端會失去登入資訊；遮蔽只適用模型副本。
    """
    # Connection: keep-alive, X-Custom-Hop 表示列出的名稱也只適用於這一段連線。
    # 除標準 HOP 清單外，這些動態指定的 header 也要移除。
    # 使用 (key, value) 清單而非字典，保留多個 Set-Cookie 等不能隨便合併的 header。
    connection = {part.strip().lower() for key, value in headers
                  if key.lower() == b"connection" for part in value.decode("latin-1").split(",")}
    blocked = HOP | connection
    return [(key, value) for key, value in headers if key.decode("latin-1").lower() not in blocked]


def model_request(request, body):
    """模型使用解析後副本；轉送時使用原始 bytes，不能把遮蔽值送給後端。

    query 使用清單保留重複參數。一般 header 保留，同名值以逗號合併供現有
    特徵程式使用；實際轉送仍保留重複項。敏感值在模型副本中遮蔽。
    JSON/form 支援欄位解析；其他可解碼內容保留文字，不解析檔案結構或二進位內容。

    輸入 request：FastAPI/Starlette 的請求物件；body：已從請求讀出的原始 bytes。
    輸出：可傳給 Predictor.predict 的模型請求字典，不會轉送 HTTP，也不改寫輸入 body。

    以 POST /products?order=asc&page=2 為例：
    method 保存 POST；path 保存 /products；raw_query 保存 order=asc&page=2。
    headers 保存觀測到的 header 名稱與值，但 Authorization/Cookie 等值經共用函式遮蔽。
    body 是依 Content-Type 解析後的副本，raw_body 是原始 UTF-8 文字視角。
    重複 query 如 tag=a&tag=b 的解析值是清單，但 raw_query 仍保留原寫法。

    內部變數 headers 是供模型使用的字典，重複同名 header 用逗號串接；不影響實際轉送。
    content_type 去掉 ;charset=utf-8 等參數，只用主類型選解析方式。
    JSON 解析失敗時保留字串，form 使用 parse_qs 保留空值與重複欄位。
    無法以 UTF-8 解讀的二進位只放 unsupported_binary_bytes 長度標記，不分析其檔案內容。
    非 JSON/form 的可解碼內容走文字分支；並沒有專門解析 multipart 每個檔案或欄位。

    最後經 prepare_request 套用與訓練一致的遮蔽與格式規則。
    這些規則會移除憑證欄位內的文字訊號，因此不能宣稱模型可分析被遮蔽的密碼／token 原值。
    """
    # 共用訓練時的輸入規則：只在模型副本遮蔽憑證，不修改底下 proxy 保存的 body bytes。
    from request_input import prepare_request
    headers = {}
    # ASGI 提供原始 header bytes；latin-1 可逐位元映射，不因非 UTF-8 的 header 值解碼失敗。
    # 名稱改小寫僅供模型比對；合併同名值只是現有特徵介面的表示方式。
    for key, value in request.headers.raw:
        name, value = key.decode("latin-1").lower(), value.decode("latin-1")
        headers[name] = headers[name] + ", " + value if name in headers else value
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    parsed = None
    raw_body = ''
    # 空本文用空字串；無法以 UTF-8 解讀的二進位用 raw_body=None 表示未提供可用文字。
    # 二進位目前只給長度標記，並未真正掃描檔案內容。
    if body:
        try:
            text = body.decode('utf-8')
            raw_body = text
        except UnicodeDecodeError:
            text = None
            raw_body = None
        if text is None:
            parsed = {'unsupported_binary_bytes': len(body)}
        elif content_type == "application/json" or content_type.endswith("+json"):
            try:
                parsed = json.loads(text)
            except ValueError:
                parsed = text  # 畸形 JSON 也可能包含攻擊訊號，不默默當作空白。
        elif content_type == "application/x-www-form-urlencoded":
            parsed = parse_qs(text, keep_blank_values=True)
        else:
            parsed = text
    # raw_path/raw_query 保留百分比編碼與重複參數，避免用解析 URL 重新拼接而改變訊號。
    # prepare_request 會遮蔽 Authorization、Cookie、password 等模型副本中的敏感值。
    return prepare_request({'method': request.method,
        'path': request.scope.get('raw_path', request.url.path.encode('utf-8')).decode('latin-1'),
        'raw_query': request.scope['query_string'].decode('latin-1'),
        'headers': headers, 'body': parsed, 'raw_body': raw_body})


@asynccontextmanager
async def lifespan(app):
    """共用 HTTP 連線池；模型只載入一次，不在每個請求重新讀檔。

    輸入 app：FastAPI 應用程式；這是一個 async context manager，不是一般 API 路由。
    yield 之前是啟動階段，yield 期間服務可收請求，離開時釋放 HTTP client。

    設定範例：MEDUSA_UPSTREAM=http://127.0.0.1:9000，GATEWAY_MODEL_DIR 指向 inference 資料夾。
    若未設定模型目錄，僅做轉送；若設定但載入失敗，也僅做轉送並記 warning。
    既有規則拒絕 exploratory 模型，包含新版 offline 的探索性產物，不能直接當正式閘道模型。
    上游 URL 格式本身不合法則在載入模型前拋錯，服務不能帶著錯誤轉送地址啟動。

    app.state.upstream 是上游基底網址；predictor 是已載入模型或 None。
    model_lock 是同程序的推論互斥鎖；client 是重用連線池的 HTTPX AsyncClient。
    這些狀態讓每筆 proxy 不必重新讀模型、建立整個 client。
    若多個 uvicorn worker，每個程序各跑一次 lifespan，不共享 Python 物件。

    目前沒有在這裡執行 Predictor.self_test；部署者仍應先於目標環境手動完成套件自測。
    模型載入失敗只告警而不停止服務，是目前原型的行為，不等於服務已具有偵測保護。
    """
    # MEDUSA_UPSTREAM 指向真正電商後端，預設為本機 9000。
    # GATEWAY_MODEL_DIR 指向包含 model.json、metadata 與 manifest 的完整 inference 目錄。
    # 模型路徑可隨部署位置指定；沒有把訓練時的絕對路徑寫死在程式中。
    upstream = os.environ.get("MEDUSA_UPSTREAM", "http://127.0.0.1:9000").rstrip("/")
    if not upstream.startswith(("http://", "https://")):
        raise ValueError("MEDUSA_UPSTREAM 必須是 HTTP(S) 網址")
    app.state.upstream = upstream
    app.state.predictor = None
    model_dir = os.environ.get("GATEWAY_MODEL_DIR")
    # 有設定模型才嘗試載入。缺檔、版本／雜湊不符等錯誤只記類型，避免錯誤訊息洩漏資料。
    # 載入失敗時 predictor 維持 None，服務仍做反向代理，不會假裝正在執行模型分析。
    if model_dir:
        try:
            from predict import Predictor
            candidate = Predictor(Path(model_dir))
            # 這是既有的試跑模型限制，與人工審核無關；正式部署不能隱藏試跑標記。
            if candidate.exploratory:
                raise ValueError('候選試跑模型不可當作正式閘道模型')
            app.state.predictor = candidate
        except Exception as error:
            # 只記錯誤類型，不記錄 Token、body 或可能包含敏感資訊的錯誤內容。
            log.warning("model_load_failed type=%s", type(error).__name__)
    else:
        log.warning("model_disabled: GATEWAY_MODEL_DIR 未設定，僅轉送")
    # FastAPI lifespan 在每個服務程序啟動時執行一次，模型與 HTTP client 均在該程序內重用。
    # 若 uvicorn 開多個 worker，各 worker 會有自己的模型、鎖與連線池，並非跨程序共用。
    app.state.model_lock = asyncio.Lock()
    # 共用連線池減少每筆重新連線的成本；離開 lifespan 時自動關閉。
    # 不自動追蹤上游重新導向，由瀏覽器處理 Location；也不讀取環境的代理設定。
    # timeout=30 是 HTTPX 連線／讀寫等階段的逾時設定，不是含模型排隊的端到端總期限。
    async with httpx.AsyncClient(timeout=30, follow_redirects=False, trust_env=False) as client:
        app.state.client = client
        yield


# 關閉自動 API 文件路由，避免 /docs 等網址被 gateway 自己接走，而沒有交給電商後端。
app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


# path:path 接住多層路徑，統一代理下列 HTTP 方法；WebSocket 不會進入這個處理函式。
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def proxy(request: Request, path: str):
    # 本版讀取整個本文；正式使用前須增加大小限制及串流支援。
    # 同一份 bytes 一份用來產生模型副本，一份原封不動交給上游。
    # 目前請求與回應都會整段存入記憶體，大檔案／大量並行請求可能造成記憶體壓力。
    """輸入 request 是進站請求；path 是 FastAPI 捕獲的路徑參數，實際上游路徑仍取 raw_path。
    輸出 Response：一般情況沿用上游狀態碼、可轉送 header 與回應 bytes。
    若上游逾時回 504；若發生其他 HTTPX 連線錯誤回 502，不偽造成功狀態。

    單筆執行順序：
    1. 讀完整 body bytes，保留供後端使用，這時尚未改寫／遮蔽原始本文。
    2. 有 predictor 才建立模型副本，取得鎖並等待工作執行緒完成預測。
    3. 僅寫 label/exploratory 到 log；預測攻擊或推論失敗都繼續往後走。
    4. 用設定的上游＋原始 path/query 建立目標，移除逐段 header 與待重建的 Host/Content-Length。
    5. 用原始 body 送往上游，讀回原始回應 bytes，回傳瀏覽器。
    6. finally 關閉本次上游 response，讓連線可被池管理，不會因例外漏掉釋放。

    例如模型副本的 password 變成 [REDACTED]，原始登入請求送到 Medusa 的 password 仍不變。
    若模型報 sqli，目前不會回 403、不會改請求內容，也不會阻止 SQLi 到達上游。
    若上游本來回 401/422/500，本函式會保留該狀態，讓網站按真正結果處理。

    效能限制：await 不等於不等待；本請求仍需等推論與上游回應，鎖也可能造成排隊。
    asyncio.to_thread 只把 predict 移離事件迴圈；解析模型副本仍在事件迴圈內。
    目前沒有硬推論逾時／有界佇列，請求與回應也都整段暫存在記憶體。
    因此這是有分析功能的轉送骨架，尚不保證大檔、串流或高併發情境可用。
    """
    body = await request.body()
    predictor = request.app.state.predictor
    if predictor is not None:
        try:
            # 模型運算放到執行緒，避免直接阻塞事件迴圈；鎖避免同物件並行問題。
            # 目前沒有硬性推論逾時，正式整合應改成獨立 worker 與有界佇列。
            # lock 讓同程序同時間只跑一筆模型推論；網站其他非阻塞工作仍可進行。
            # model_request 的解析仍在事件迴圈執行，只有 predictor.predict 放進工作執行緒。
            # 此處會等推論完成才轉送，所以「不封鎖」不代表「零額外延遲」。
            async with request.app.state.model_lock:
                result = await asyncio.to_thread(predictor.predict, model_request(request, body))
            # 只記類別與試跑標記，不把原始 header、密碼、Cookie 或本文寫入 log。
            # 此紀錄不是封鎖動作，也不能用來證明模型判斷正確。
            log.info("prediction label=%s exploratory=%s", result["label"], result["exploratory"])
        except Exception as error:
            log.warning("prediction_failed type=%s", type(error).__name__)
            # 分析失敗照常轉送；這是只告警模式，不是安全封鎖策略。
    # 使用原始路徑與 query，避免重新編碼改變 %2F、重複參數等內容。
    # 上游位址來自服務設定，路徑與 query 來自原始請求；不使用模型副本的遮蔽內容。
    # 此處預期 raw URL 已採 ASCII／百分比編碼，不會將 %2F 解碼成另一層路徑。
    raw_path = request.scope.get("raw_path", request.url.path.encode()).decode("ascii")
    query = request.scope["query_string"].decode("ascii")
    target = request.app.state.upstream + raw_path + ("?" + query if query else "")
    # 原始 Authorization/Cookie 仍須交給後端完成登入情境；遮蔽只發生在模型副本。
    # Host 與 Content-Length 交由 HTTPX 依上游主機與原始 bytes 正確重建。
    headers = [(k, v) for k, v in forwarded_headers(request.headers.raw)
               if k.lower() not in {b"host", b"content-length"}]
    try:
        # Host/Content-Length 交由 HTTP client 依上游位址與原始本文重新建立。
        upstream_request = request.app.state.client.build_request(request.method, target, headers=headers, content=body)
        # stream=True 先取得回應，但下方仍將所有區塊合併後才回傳，並非完整串流代理。
        upstream = await request.app.state.client.send(upstream_request, stream=True)
        try:
            # 使用 raw bytes，避免自動解壓後仍保留 Content-Encoding 導致瀏覽器解讀錯誤。
            content = b"".join([chunk async for chunk in upstream.aiter_raw()])
            response = Response(content, status_code=upstream.status_code)
            # 保留可轉送的重複回應 header，例如多個 Set-Cookie；移除逐段連線 header。
            response.raw_headers = forwarded_headers(upstream.headers.raw)
            return response
        finally:
            # 無論正常回傳或讀取途中拋錯，都釋放上游連線，避免連線池耗盡。
            await upstream.aclose()
    # 代理自己無法完成上游連線時才產生 504/502；上游已正常回傳的 4xx/5xx 則照實轉送。
    except httpx.TimeoutException:
        return Response("Upstream timeout", status_code=504)
    except httpx.HTTPError:
        return Response("Upstream unavailable", status_code=502)
