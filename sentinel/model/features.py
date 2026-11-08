"""訓練與推論共用的特徵處理；不使用平台、回應或憑證欄位。"""
import json
import re
from urllib.parse import unquote, urlsplit

# 修改特徵內容或順序時須更新版本，並重新訓練模型。
VERSION = 3
LABELS = ["normal", "sqli", "xss"]
# 計算常見 SQLi／XSS 詞法訊號的出現次數，並非完整攻擊判定規則。
PATTERNS = [r"\b(or|and)\b", r"\bunion\b", r"\bselect\b", r"\bsleep\b|\bbenchmark\b",
            r"--|/\*|\*/", r"<script\b", r"\bon\w+\s*=", r"javascript\s*:"]
SENSITIVE = re.compile(r"password|passwd|secret|token|authorization|cookie|api.?key|access.?key|storefront.?key|session.?id", re.I)


def clean(value):
    """遞迴移除敏感欄位，包含物件與清單內的巢狀資料。

    依欄位名稱判斷，並非任意文字的完整去識別化工具。
    例如 password 欄位會排除，但藏在普通文字中的憑證不一定能辨識。
    """
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items() if not SENSITIVE.search(str(k))}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def text(value):
    # 先解析 JSON 本文，才能在計算特徵前排除敏感欄位。
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            # 嘗試解析表單字串；其他純文字格式暫不支援。
            if "=" in value and not value.lstrip().startswith(("{", "[")):
                from urllib.parse import parse_qs
                value = parse_qs(value, keep_blank_values=True)
            else:
                return value  # 純文字／畸形 JSON 仍計算訊號，不再默默捨棄。
    return json.dumps(clean(value), ensure_ascii=False, sort_keys=True)


def header_features(headers):
    """檢查所有傳入 header；一般值保留訊號，敏感值只保留統計。

    不儲存 header 詞彙表或 Token 字串，避免靠固定網域／憑證記答案。
    URL 型 header 去掉主機名稱；目前不涵蓋主機名稱內的攻擊。
    字典格式無法保留同名重複 header，重複標頭／走私分析不在本版範圍。
    """
    ordinary, protected = {}, []
    for name, value in headers.items():
        name, value = str(name).lower(), str(value)
        if name in {"x-request-id", "traceparent", "tracestate"}:
            value = "[ID]"
        if SENSITIVE.search(name):
            protected.append(value)
            continue
        if name in {"host", ":authority"}:
            value = "[AUTHORITY]"
        elif name in {"origin", "referer"}:
            try:
                parsed = urlsplit(value)
                if parsed.netloc:
                    value = parsed.path + ("?" + parsed.query if parsed.query else "")
            except ValueError:
                pass  # 格式無效仍保留字元訊號，避免畸形 header 使推論中斷。
        ordinary[name] = value
    # 已遮蔽的值沒有原始長度，不把遮蔽字樣誤算成憑證長度。
    lengths = [min(len(v), 4096) for v in protected if v not in {"[REDACTED]", "[ID]"}]
    result = [len(headers), len(protected), sum(lengths), max(lengths, default=0)]
    raw = json.dumps(ordinary, sort_keys=True, ensure_ascii=False)
    for value in [raw.lower(), unquote(raw).lower()]:
        result += signals(value)
    return result


def signals(value):
    """固定 16 維：長度、7 種特殊字元次數、8 種詞法訊號次數。"""
    return [len(value), *[value.count(c) for c in ["%", "'", '\"', "<", ">", ";", "="]],
            *[len(re.findall(pattern, value)) for pattern in PATTERNS]]


def features(request):
    """將解析後的請求轉成固定長度的數字清單，供 XGBoost 使用。

    前 8 個特徵是 HTTP 方法與 Content-Type 的 0／1 值。
    接著分別處理 query、body、path；每部分再分原文、一次解碼兩組。
    每組含 16 維；query、body、path 各 32 維，header 36 維，共 140 維。
    不在這裡學習詞彙表或使用標籤，因此推論時可直接重用。
    query/body 預期是已解析的物件；此基準未實作完整協定驗證。
    """
    # 將 HTTP 方法與 Content-Type 轉為 0／1 特徵。
    result = [int(request.get("method", "GET").upper() == m)
              for m in ["GET", "POST", "PUT", "PATCH", "DELETE"]]
    headers = {k.lower(): v for k, v in request.get("headers", {}).items()}
    content_type = str(headers.get("content-type", "")).lower()
    result += [int(t in content_type) for t in ["json", "form", "multipart"]]
    # query 與 body 分開取特徵；不使用路徑識別碼，降低記住平台的可能。
    # path 參數取自真實路徑；未解析的請求仍以完整 path 計算訊號。
    # 沒有對 query/body 挑名稱：所有非敏感巢狀欄位都會參與。
    path = request.get("path_parameters", request.get("path", ""))
    parts = [text(request.get("query", {})), text(request.get("body")),
             path if isinstance(path, str) else text(path)]
    for raw in parts:
        # 原始文字與一次 URL 解碼後的文字各保留一組特徵。
        for s in [raw.lower(), unquote(raw).lower()]:
            result += signals(s)
    result += header_features(headers)
    return result
