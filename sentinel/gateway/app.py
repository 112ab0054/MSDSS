"""Medusa 觀察型閘道：請求 → 模型副本 → XGBoost → 原始請求轉送。

所有支援的HTTP方法與路徑均送入模型分析，再照常轉送 Medusa。
推論序列處理，忙碌時等待而不略過；模型判為攻擊也只告警，仍照常轉送。
預設載入本目錄 model/ 的使用者已訓練模型；GATEWAY_MODEL_DIR 可另指定完整推論套件。
模型失敗時僅轉送。離線模型可供 demo，紀錄仍標示 offline，不冒充實機驗證。
啟動與限制見同目錄 README；不把原始請求、密碼或 Cookie 寫入日誌。
"""
# asyncio 負責非同步等待；HTTP 轉送用 httpx，API 入口與回應分別由 FastAPI／Starlette 處理。
# 模型仍使用既有 predict.py，不在這裡重新訓練 XGBoost。
import asyncio
from contextlib import asynccontextmanager
import json
import logging
import math
import os
from pathlib import Path
import re
import sys
import uuid
from urllib.parse import parse_qs

import httpx
from fastapi import FastAPI, Request
from starlette.responses import Response, StreamingResponse

# 依程式位置找共用模型程式；Windows/Linux 換位置後不必修改原始碼。
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'model'))
# 隨程式位置找已提供的推論套件；不依賴目前工作目錄，也不寫死 Colab／Windows 路徑。
DEFAULT_MODEL = Path(__file__).resolve().parent / 'model'
# 使用 uvicorn 的日誌體系，讓啟動狀態與預測結果可在終端機看到。
log = logging.getLogger('uvicorn.error.gateway')
# HOP 是逐段連線標頭，例如 Connection／Transfer-Encoding；每段代理連線要自行管理。
# 移除這些標頭不等於只看少數 header，其他觀測值仍保留給模型副本及後端。
HOP = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
       'te', 'trailer', 'transfer-encoding', 'upgrade', 'proxy-connection'}
# API參考清單僅供文件／驗證；所有支援的HTTP路徑都分析，不依賴清單檔。


class ForwardURL(httpx.URL):
    """HTTPX 預設會折疊 /a/../b；轉送時覆寫 raw_path，保留真正的請求目標。"""
    def __init__(self, origin, target):
        # origin 是 Medusa 主機位址；target 是原始路徑加 query，例如 b'/store/products?q=A%2fb'。
        # 保留 target 供傳輸層取用，避免 HTTPX 把 /a/../b 自動整理成 /b，改變原請求。
        self.target = target
        super().__init__(origin.copy_with(raw_path=target))

    @property
    def raw_path(self):
        # @property 讓 HTTPX 讀取 url.raw_path 時得到我們保存的原始 bytes。
        return self.target


def forwarded_headers(headers):
    """移除只屬於單段連線的 header；用清單保留多個 Set-Cookie 等重複值。"""
    # Connection: keep-alive, X-Temp 表示 X-Temp 也只屬於當前這段連線，要連同標準 HOP 移除。
    # header 使用 bytes 成對清單；latin-1 可逐位元映射，不要求 header 值一定是 UTF-8。
    connection = {part.strip().lower() for key, value in headers if key.lower() == b'connection'
                  for part in value.decode('latin-1').split(',')}
    # HOP | connection 是兩個集合的聯集。其餘項目原樣留下，重複 Set-Cookie 不會被字典覆蓋。
    return [(k, v) for k, v in headers if k.decode('latin-1').lower() not in HOP | connection]


def model_request(request, body):
    """產生模型副本；憑證遮蔽只影響副本，原始 body bytes 仍供後端登入使用。"""
    # 共用訓練端入口，確保同一個 HTTP 請求在訓練與 gateway 轉成相同格式及遮蔽規則。
    from request_input import prepare_request
    # 這個 headers 只供模型副本；原始 request.headers.raw 仍保留給後端轉送。
    headers = {}
    # 模型副本把 header 名稱統一小寫，同名值用逗號合併；實際轉送仍保留原始重複項。
    for key, value in request.headers.raw:
        name, value = key.decode('latin-1').lower(), value.decode('latin-1')
        headers[name] = headers[name] + ', ' + value if name in headers else value
    # 只取分號前的媒體類型，例如 application/json; charset=utf-8 → application/json。
    # 它只用來選解析方式，不代表模型只檢查 Content-Type。
    content_type = request.headers.get('content-type', '').split(';', 1)[0].lower()
    try:
        # JSON/form 等文字本文使用 UTF-8；無法解碼時以 None 表示沒有可供分析的原文。
        text = body.decode('utf-8')
    except UnicodeDecodeError:
        text = None
    # text/raw_body 保存文字寫法；parsed/body 保存解析後的結構，兩者用途不同。
    # 空本文為 text=''、parsed=None，不補造有內容的請求。
    parsed = text if body else None
    if text is None:
        parsed = {'unsupported_binary_bytes': len(body)}  # 不宣稱已分析檔案內容。
    elif body and (content_type == 'application/json' or content_type.endswith('+json')):
        try:
            # 正常 JSON 解析為字典／陣列等型別，讓共用函式能遮蔽巢狀 password 等欄位。
            parsed = json.loads(text)
        except ValueError:
            pass  # 畸形 JSON 仍保留文字訊號，不能當成沒有本文。
    elif body and content_type == 'application/x-www-form-urlencoded':
        # form 的 tag=a&tag=b 解析為 tag: [a, b]，保留重複值與空值；限制最多 1000 個欄位。
        parsed = parse_qs(text, keep_blank_values=True, max_num_fields=1000)
    # raw 保留百分比編碼、重複 query 與空白；共用 prepare_request 與訓練採相同規則。
    return prepare_request({'method': request.method,
        'path': request.scope.get('raw_path', request.url.path.encode()).decode('latin-1'),
        'raw_query': request.scope['query_string'].decode('latin-1'),
        'headers': headers, 'body': parsed, 'raw_body': text})


def analyze(predictor, request, body):
    """在工作執行緒解析與推論；只記結果／模式，錯誤也只記類型，避免洩漏憑證。"""
    try:
        # model_request 建立副本 → predictor.predict 以共用 features 轉為數值向量 → XGBoost 回傳分類。
        # 結果含 label、三類 probabilities、mode、exploratory。
        # predict.py 先用與訓練相同的 features 產生 2402 維向量，再呼叫 XGBClassifier.predict_proba。
        # 三類順序為 normal／sqli／xss，取最大機率的類別（argmax），沒有另加 0.5 或 0.9 門檻。
        # 這裡不修改原請求，也不依結果產生封鎖回應。
        result = predictor.predict(model_request(request, body))
        # proxy 入口已驗證／產生 UUID；從 state 取值，不需修改模型看到的原始 headers。
        request_id = request.state.request_id
        # 只記判斷與來源標記；offline 不冒充實測，機率也不是已驗證的正確率。
        log.info('prediction label=%s mode=%s exploratory=%s request_id=%s probabilities=%s',
                 result['label'], result.get('mode', 'unspecified'), result['exploratory'],
                 request_id, json.dumps(result.get('probabilities', {}), sort_keys=True))
    except Exception as error:
        log.warning('prediction_failed request_id=%s type=%s', request.state.request_id, type(error).__name__)


@asynccontextmanager
async def lifespan(app):
    """每個服務程序只載入一次模型並共用連線池；設定失敗與模型失敗分開處理。"""
    # MEDUSA_UPSTREAM 指真正後端的 origin，例如 http://127.0.0.1:9000，不是 gateway 自己的 8080。
    # 由環境變數指定部署位置，沒有寫入訓練機的 Windows／Linux 絕對路徑。
    url = httpx.URL(os.getenv('MEDUSA_UPSTREAM', 'http://127.0.0.1:9000'))
    # 不接受帳密、API 子路徑或 query，避免之後拼接目標時發生錯誤或外洩憑證。
    if (url.scheme not in ('http', 'https') or not url.host or url.userinfo
            or url.raw_path != b'/' or url.fragment):
        raise ValueError('MEDUSA_UPSTREAM 請填不含帳密、路徑、query 的 HTTP(S) origin')
    # 這是「等待模型」的告警門檻，預設0.2秒；超過後仍等完成；與下面上游 HTTP 的 30 秒逾時不同。
    timeout = float(os.getenv('GATEWAY_ANALYSIS_TIMEOUT', '0.2'))
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('GATEWAY_ANALYSIS_TIMEOUT 必須是有限正數（秒）')
    # app.state 保存此程序共用狀態，proxy 收到每筆請求後可重用，不必重載設定或模型。
    app.state.upstream, app.state.analysis_timeout = url, timeout
    # predictor=None 表示尚無可用模型；analysis_task=None 表示目前沒有背景分析工作。
    app.state.predictor, app.state.analysis_task = None, None
    app.state.analysis_lock = asyncio.Lock()
    # 未設定時使用隨專案提供的 model/；環境變數有值時改用指定套件，空字串則明確停用模型。
    # model.json 是樹模型，metadata 是特徵與類別契約，manifest 用來確認檔案沒有混版。
    # 不重新訓練模型、不讀 test/validation 選門檻，只載入使用者提供的訓練結果。
    directory = os.getenv('GATEWAY_MODEL_DIR', str(DEFAULT_MODEL))
    if directory:
        try:
            from predict import Predictor
            # ../model/predict.py 是專案推論入口；model/ 內另附使用者訓練時的同版程式副本。
            # Predictor 會核對目前 import 的 predict/features/request_input 與套件 SHA 是否相同，
            # 以及特徵版本、類別順序、向量維度，再把 model.json 載入 XGBClassifier。
            # 因此更新訓練套件時必須連同同版程式一起更新，不能只替換一份權重或單一 .py。
            predictor = Predictor(Path(directory))
            # 用訓練側保存的三筆探針核對三類機率，確認目前 Python 環境能重現原套件輸出。
            # 自測通過才設為可用模型；這不是測試集準確率或平台漏洞／防護率。
            predictor.self_test()
            app.state.predictor = predictor  # 觀察模式容許 offline，但不可隱藏探索性標記。
            log.info('model_ready mode=%s exploratory=%s', predictor.mode, predictor.exploratory)
        except Exception as error:
            log.warning('model_load_failed type=%s', type(error).__name__)
    else:
        log.warning('model_disabled: GATEWAY_MODEL_DIR 為空，僅轉送')
    # 不追蹤 302，交由瀏覽器處理；不沿用環境代理。30 秒是上游 HTTP 階段逾時。
    async with httpx.AsyncClient(timeout=30, follow_redirects=False, trust_env=False) as client:
        app.state.client = client
        # yield 期間 FastAPI 開始處理請求；服務結束離開 async with 時，自動關閉連線池。
        yield


async def response_body(upstream):
    """逐塊原樣回傳，保留 gzip 等編碼；完成、取消或出錯時都關閉上游回應。"""
    try:
        # aiter_raw 不先解壓 gzip，避免本文已解壓、header 卻仍寫 Content-Encoding: gzip。
        # 每次 yield 一個區塊，讓回應逐步送回瀏覽器，不必先把整份下載內容存進記憶體。
        async for chunk in upstream.aiter_raw():
            yield chunk
    finally:
        await upstream.aclose()


# 關閉 /docs、/redoc、/openapi.json，讓這些路徑也照一般請求轉交 Medusa，不被內建文件接走。
app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


# 共用HTTP入口：所有路徑分析後轉送；77項清單不限制偵測範圍。
# {path:path} 能接多層路徑；目前支援以下七種方法，不處理 WebSocket。
@app.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
async def proxy(request: Request, path: str):
    """所有支援的HTTP請求先分析再轉送；是否成功由Medusa決定。"""
    # 每筆請求先取得追蹤編號。只接受單一、標準連字號 UUID，避免重複 header 產生歧義。
    # 沒帶、格式錯誤或帶多個值，都重新產生 UUID；不把任意用戶文字當成日誌編號。
    identifiers = request.headers.getlist('x-request-id')
    incoming_id = identifiers[0] if len(identifiers) == 1 else ''
    request.state.request_id = incoming_id if re.fullmatch(
        r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', incoming_id
    ) else str(uuid.uuid4())
    # 只放在 request.state，新增 UUID 不加入模型副本，避免影響現有模型特徵與分數。
    # 呼叫端原本帶的 headers 仍按既有模型輸入規則處理，不修改訓練／推論契約。
    # 保留原始路徑，不以文件清單或URL解碼結果篩選模型輸入。
    raw_path = request.scope.get('raw_path', request.url.path.encode())
    body, state = await request.body(), request.app.state
    if state.predictor is not None:
        # 所有請求以backpressure等待同一個模型；不再busy略過。
        async with state.analysis_lock:
            # 前一個客戶端若中斷，其shield保護的推論仍須完成，避免並行存取模型。
            previous = state.analysis_task
            if previous is not None and not previous.done():
                await asyncio.shield(previous)
            task = asyncio.create_task(asyncio.to_thread(analyze, state.predictor, request, body))
            state.analysis_task = task
            try:
                await asyncio.wait_for(asyncio.shield(task), state.analysis_timeout)
            except asyncio.TimeoutError:
                # 這是等待告警門檻，非取消／略過門檻；仍等本筆推論完成再轉送。
                log.warning('analysis_slow: request_id=%s 等待本筆推論完成，沒有略過', request.state.request_id)
                await asyncio.shield(task)
    # 不論是否偵測、模型成功或失敗，都走到轉送區。query 保留重複參數、百分比編碼與順序。
    query = request.scope['query_string']
    # 組成 Medusa 的目標 URL，使用原始 path/query，而不是已遮蔽的模型副本。
    target = ForwardURL(state.upstream, raw_path + (b'?' + query if query else b''))
    # 保留原始 Authorization／Cookie 供後端認證，僅移除逐段標頭及由 HTTPX 重建的 Host/Content-Length。
    headers = [(k, v) for k, v in forwarded_headers(request.headers.raw)
               if k.lower() not in {b'host', b'content-length', b'x-request-id'}]
    # 轉送時只保留入口決定的一個編號；即使 Connection 要求移除它，也重新補上。
    headers.append((b'x-request-id', request.state.request_id.encode('ascii')))
    try:
        # 直接建立 Request，不合併共用 client 的 CookieJar，避免不同使用者 Cookie 互相串用。
        # outgoing 是要送給 Medusa 的 HTTP 請求，方法、header、body 都來自原始進站請求。
        # 不用 client.build_request，因為它會合併共用 client 的 Cookie，可能串用不同訪客的登入狀態。
        outgoing = httpx.Request(request.method, state.upstream, headers=headers, content=body)
        outgoing.url = target  # Request 建構器會複製 URL，最後才指定以保留 raw_path 覆寫。
        # 這一行才真正送出 HTTP 到 Medusa；stream=True 先取得回應標頭，再由 response_body 逐塊讀本文。
        upstream = await state.client.send(outgoing, stream=True)
        # Medusa 的 200、401、404、422、500 等狀態碼原樣回給網站，不拿來改寫模型標籤。
        response = StreamingResponse(response_body(upstream), status_code=upstream.status_code)
        # 原樣保留可轉送的重複回應 header，例如多個 Set-Cookie，讓各瀏覽器收到自己的登入 Cookie。
        response.raw_headers = [(k, v) for k, v in forwarded_headers(upstream.headers.raw)
                                if k.lower() != b'x-request-id']
        # 同名 header 由 gateway 統一設定，避免上游另產生編號導致日誌與回應對不起來。
        response.headers['x-request-id'] = request.state.request_id
        return response
    # 只有 gateway 與後端的連線／傳輸失敗才在這裡產生 504 或 502；正常收到的後端錯誤照實回傳。
    except httpx.TimeoutException:
        return Response('Upstream timeout', status_code=504, headers={'X-Request-ID': request.state.request_id})
    except httpx.HTTPError:
        return Response('Upstream unavailable', status_code=502, headers={'X-Request-ID': request.state.request_id})
