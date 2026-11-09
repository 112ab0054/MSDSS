"""採集、訓練、推論共用的請求格式與憑證遮蔽規則。

只遮蔽憑證值；普通 ID、email、大小寫、空白與編碼寫法保留。
raw_query/raw_body 是原文視角，query/body 是解析視角，兩者分開保存。
None 表示沒有取得原文；空字串表示確實取得一段空內容，不能混為一談。
本模組產生模型使用的副本；gateway 轉送後端時仍用原始 bytes。
"""
import json
import re
from urllib.parse import parse_qs, unquote_plus, urlsplit

INPUT_VERSION = 3
# 依欄位名稱辨識憑證，採寬鬆比對，包含巢狀欄位；並非個資或所有秘密的通用偵測器。
# 例如一般 email 不會自動隱去；呼叫端仍須避免任意記錄整筆請求。
SENSITIVE = re.compile(r'password|passwd|authorization|cookie|token|secret|api.?key|access.?key|storefront.?key|session.?id|recovery.?codes|backup.?codes|otpauth|qr.?code', re.I)
REDACTED = '[REDACTED]'


def redact_fields(value, key=''):
    # 先檢查目前欄位名：若整個欄位是憑證，連裡面的清單／物件一起遮蔽。
    # 否則才遞迴進入字典和陣列，避免只遮蔽最外層而漏掉 address.password 等欄位。
    """輸入 value 可為任意 JSON 型別，key 是目前欄位名，最外層預設空字串。
    輸出同樣結構的新物件；若 key 符合 SENSITIVE，整個值改成 [REDACTED]。
    例如 {'profile': {'password': 'secret', 'city': 'Taipei'}} 的 city 保留，但 password 遮蔽。
    list 逐項遞迴；普通字串直接保留；otpauth:// 開頭的 MFA 祕密 URI 額外遮蔽。
    依名稱遮蔽不是通用資料外洩偵測，無法辨識所有藏在無關欄位中的祕密。
    """
    if SENSITIVE.search(key):
        return REDACTED
    if isinstance(value, dict):
        return {k: redact_fields(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_fields(v) for v in value]
    if isinstance(value, str) and value.lower().startswith('otpauth://'):
        return REDACTED
    return value


def redact_query(raw):
    """逐段替換憑證 query 值，保留參數順序、重複名稱與其他值的編碼。

    不先 parse 再 urlencode，因為重建可能改寫 %2f、+、空值等攻擊訊號。
    只在判定欄位名時解碼，因此 %74oken 也能被視為 token。

    輸入 raw 是 query 或 form 原始文字，不包含前面的問號；輸出仍為字串。
    例如 page=2&token=abc&page=3 → page=2&token=[REDACTED]&page=3。
    以 & 分段，再只用第一個 = 分出 key/value，因此值中其他 = 不會被額外拆開。
    使用 unquote_plus 只判斷欄位名是否敏感，不把整段 query 解碼後重新編碼。
    沒有 = 的片段原樣保留，普通值的大小寫、百分比編碼與順序也保持不變。
    """
    result = []
    for part in str(raw).split('&'):
        key, sep, value = part.partition('=')
        result.append(key + sep + (REDACTED if sep and SENSITIVE.search(unquote_plus(key)) else value))
    return '&'.join(result)


def redact_path(path):
    # Sylius 訂單路徑的 tokenValue 本身就授予存取能力，因此視為憑證。
    # 普通商品 ID 不套這個遮蔽規則，避免丟失有用的路徑訊號。
    """輸入 path：路徑字串；輸出：對 Sylius 訂單存取 token 段做遮蔽後的路徑。
    例如 /api/v2/shop/orders/secret-token/items → /api/v2/shop/orders/[REDACTED]/items。
    此規則只針對已知路徑，不會自動把一般商品代碼或地址 ID 當成憑證。
    這是模型／證據副本的處理，不能把遮蔽後的路徑拿去存取真正訂單。
    """
    return re.sub(r'(/api/v2/shop/orders/)[^/?#]+', r'\1[REDACTED]', str(path))


def redact_target(target):
    """輸入 target：包含 path 與可選 ?query 的請求目標字串。
    輸出：分別套用 redact_path 與 redact_query 後重新接回的字串。
    partition 只在第一個 ? 分段，保留是否原本帶問號的資訊。
    此處不正規化普通路徑、不發送請求，也不依攻擊標籤選擇遮蔽方式。
    """
    path, sep, query = str(target).partition('?')
    return redact_path(path) + (sep + redact_query(query) if sep else '')


def redact_json_text(raw):
    """找出 JSON 敏感值的字元範圍，再只替換那些範圍。

    若先 json.loads 再 json.dumps，空白、跳脫或鍵排列可能改變。
    此處用解碼器辨識值的結束位置，保留其他原始字元；不拿正則硬拆巢狀 JSON。

    輸入 raw：完整 JSON 文字；輸出：只有敏感欄位值被替換的 JSON 文字。
    JSON 結構畸形時可能拋 ValueError/IndexError/RecursionError，由 redact_body_text 處理。
    spans 保存每個敏感值的 [start, end) 字元範圍，start 包含值本身的起始引號或括號。
    例如 password 後面是整個陣列，整段陣列會換成字串 [REDACTED]，而不是只遮一個元素。
    walk 遞迴解析物件、陣列及純量；JSONDecoder 負責辨識正確的跳脫與值邊界。
    最後由右向左替換，確保尚未使用的原始索引不會因字串縮短而失效。
    """
    decoder = json.JSONDecoder()
    spans = []
    # i 是原始文字索引；walk 回傳完整值後面的索引，並沿路收集待遮蔽範圍。
    def whitespace(i):
        """輸入 i 是 JSON 原文字元位置；輸出略過空格、換行、回車及 tab 後的位置。
        這只移動解析游標，不會刪掉原文字串裡的空白。
        因此在敏感值以外，格式化空白仍保留給後續原文特徵。
        """
        while i < len(raw) and raw[i] in ' \r\n\t': i += 1
        return i
    def walk(i):
        """輸入 i 為要解析的 JSON 值起點；輸出該值結束後的位置。
        遇到 { 就循環處理鍵值對，遇到 [ 就逐項遞迴，純量交給 JSONDecoder.raw_decode。
        若鍵名敏感，直接取整個值的邊界並記入 spans；否則進入子結構繼續尋找敏感鍵。
        物件必須有冒號、項目間必須有逗號，格式不合時拋錯，避免錯位遮蔽造成祕密洩漏。
        """
        i = whitespace(i)
        if raw[i] == '{':
            i = whitespace(i + 1)
            if raw[i] == '}': return i + 1
            while True:
                key, end = decoder.raw_decode(raw, i)
                i = whitespace(end)
                if not isinstance(key, str) or raw[i] != ':': raise ValueError('invalid object')
                start = whitespace(i + 1)
                if SENSITIVE.search(key):
                    _, end = decoder.raw_decode(raw, start)
                    spans.append((start, end))
                else:
                    end = walk(start)
                i = whitespace(end)
                if raw[i] == '}': return i + 1
                if raw[i] != ',': raise ValueError('invalid object')
                i = whitespace(i + 1)
        if raw[i] == '[':
            i = whitespace(i + 1)
            if raw[i] == ']': return i + 1
            while True:
                i = whitespace(walk(i))
                if raw[i] == ']': return i + 1
                if raw[i] != ',': raise ValueError('invalid array')
                i = whitespace(i + 1)
        return decoder.raw_decode(raw, i)[1]
    end = walk(0)
    if raw[end:].strip(): raise ValueError('trailing content')
    # 從後往前替換，避免前方字串長度變動讓尚未處理的索引失準。
    for start, end in reversed(spans):
        raw = raw[:start] + json.dumps(REDACTED) + raw[end:]
    return raw


def redact_body_text(raw, content_type=''):
    # 依 Content-Type 優先識別 form/JSON，也嘗試辨識以 { 或 [ 開頭的 JSON。
    # 保留無法解析的普通文字；若畸形內容疑似帶憑證，則採整段遮蔽以免洩漏。
    """輸入 raw：原始本文文字或 None；content_type：HTTP 內容類型。
    輸出遮蔽後的文字或 None；raw 不是字串且不為 None 時拋 TypeError。
    form-urlencoded 使用 query 同樣的逐段規則；JSON 使用字元範圍替換。
    若 JSON 壞掉且疑似含敏感欄位，整段改為固定遮蔽訊息，避免只遮到一半。
    例如少一個結尾引號的 password 本文，不會為了保留攻擊訊號就直接外洩原密碼。
    普通不帶敏感訊號的畸形內容仍保留，因此模型有機會看見畸形 JSON 本身的特徵。
    """
    if raw is None: return None
    if not isinstance(raw, str): raise TypeError('raw body must be text')
    content_type = content_type.lower()
    if 'form-urlencoded' in content_type:
        return redact_query(raw)
    if 'json' in content_type or raw.lstrip().startswith(('{', '[')):
        try:
            return redact_json_text(raw)
        except (ValueError, IndexError, RecursionError):
            # 畸形 JSON 無法可靠定位敏感值的結束位置，不直接把可能含密碼的原文匯出。
            # 因此這類請求的原文訊號會減少；不能聲稱保留了所有敏感欄位中的攻擊內容。
            keys = re.findall(r'"((?:[^"\\]|\\.)*)"\s*:', raw)
            def sensitive_key(key):
                """輸入 key 是從畸形 JSON 中擷取到的鍵名文字，可能仍含 JSON 跳脫。
                嘗試以 JSON 規則解開後再比對 SENSITIVE，避免跳脫形式的 password 被漏掉。
                鍵名本身也無法解碼時保守回傳 True，使外層整段遮蔽，不冒險匯出可能的憑證。
                """
                try:
                    return bool(SENSITIVE.search(json.loads('"' + key + '"')))
                except ValueError:
                    return True
            if any(sensitive_key(key) for key in keys) or SENSITIVE.search(raw):
                return '[REDACTED: malformed credential-bearing body]'
    elif '=' in raw and any(SENSITIVE.search(unquote_plus(part.partition('=')[0])) for part in raw.split('&')):
        return redact_query(raw)
    return raw


def prepare_request(request):
    """將單筆請求整理為共同結構並遮蔽憑證，不補造未擷取的原文。

    headers 為名稱到值的字典；重複 header 的合併由上游輸入端處理。
    raw query 若存在就優先解析，重複參數保留成清單，空值也不丟棄。
    此函式不送 HTTP、不查資料庫，也不根據 label 或回應狀態修改輸入。

    輸入 request：一筆請求字典；輸出：共同格式的新字典，不改原 request。
    至少會提供 method、path、raw_query、query、headers、body、raw_body。
    若原輸入有 path_parameters，則額外保留其遮蔽後副本。

    缺少 method 時預設 GET；缺少 path 時用空字串；缺少 headers 時用空字典。
    若 raw_query 沒提供、path 卻包含 ?，會拆出問號後方文字。
    raw_query 存在就以它重建 query，重複欄位保留 list，例如 page=1&page=2 → ['1', '2']。
    raw_query=None 則沿用已解析 query，不補造一段看似已擷取的原文字串。
    headers 保留名稱寫法；敏感欄位值遮蔽，Referer/Location 額外檢查 URL 的 query/path 憑證。

    raw_body=None 代表沒有可用原文，raw_body='' 代表確實為空，兩者在 features 中走不同分支。
    query 解析最多接受 1000 個欄位，超過時拋 ValueError；gateway 會依現有分析失敗策略繼續轉送。
    這個共用入口是為了讓訓練／推論使用相同轉換，不是伺服器業務資料驗證器。
    """
    headers = {str(k): redact_fields(v, str(k)) for k, v in request.get('headers', {}).items()}
    for key in headers:
        if key.lower() in {'referer', 'location'} and isinstance(headers[key], str):
            headers[key] = redact_target(headers[key])
    content_type = next((str(v) for k, v in headers.items() if k.lower() == 'content-type'), '')
    path = request.get('path', '')
    raw_query = request.get('raw_query')
    if raw_query is None and '?' in path:
        path, raw_query = path.split('?', 1)
    raw_query = redact_query(raw_query) if raw_query is not None else None
    # 限制解析欄位數為 1000，超出時會拋錯，讓呼叫端決定如何處理。
    # 保留 raw_query 原寫法供特徵使用，解析值只是另一個視角。
    query = parse_qs(raw_query, keep_blank_values=True, max_num_fields=1000) if raw_query is not None else request.get('query', {})
    result = {'method': request.get('method', 'GET'), 'path': redact_path(path),
        'raw_query': raw_query, 'query': redact_fields(query), 'headers': headers,
        'body': redact_fields(request.get('body')),
        'raw_body': redact_body_text(request.get('raw_body'), content_type)}
    if 'path_parameters' in request:
        result['path_parameters'] = redact_fields(request['path_parameters'])
    return result


def from_evidence(row):
    # 從實測證據還原模型副本，優先使用真正送出的 request_target。
    # operation_path 是 /products/{id} 之類模板；將動態段對應回 path_parameters。
    # 還原後仍經 prepare_request，與 CSV 訓練及 gateway 推論保持相同處理方式。
    """輸入 row：HTTP 證據 requests 清單中的一筆，不是完整資料集樣本。
    輸出：prepare_request 整理後的模型請求副本。
    request_target 優先於較早版本的 path；urlsplit 分離實際 path/query。
    operation_path 如 /products/{id} 會建立正則，把實際 /products/123 對回 {'id': '123'}。
    使用的是 request_headers、request_body、request_body_raw，不取 response_body 當模型特徵。
    找不到模板匹配時 path_parameters 為空；不能據此聲稱取得文件所有動態參數。
    """
    target = row.get('request_target', row['path'])
    url = urlsplit(target)
    pattern = '^' + re.sub(r'\\\{[^}]+\\\}', '([^/]+)', re.escape(row.get('operation_path', ''))) + '$'
    match = re.match(pattern, urlsplit(row['path']).path)
    names = re.findall(r'\{([^}]+)\}', row.get('operation_path', ''))
    path_parameters = dict(zip(names, match.groups() if match else []))
    return prepare_request({'method': row['method'], 'path': url.path,
        'raw_query': row.get('raw_query', url.query), 'headers': row.get('request_headers', {}),
        'body': row.get('request_body'), 'raw_body': row.get('request_body_raw'), 'path_parameters':path_parameters})
