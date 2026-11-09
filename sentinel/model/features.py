"""v6 HTTP 請求特徵：基礎數值訊號＋四通道字元 n-gram 雜湊，訓練與推論共用。"""
import json
import re
from sklearn.feature_extraction.text import HashingVectorizer
from request_input import SENSITIVE, prepare_request, redact_fields

VERSION = 6
LABELS = ['normal', 'sqli', 'xss']
PATTERNS = [r'\b(or|and)\b', r'\bunion\b', r'\bselect\b', r'\bsleep\b|\bbenchmark\b',
            r'--|/\*|\*/', r'<script\b', r'\bon\w+\s*=', r'javascript\s*:']
# 固定 512 個桶不需要先看資料建立詞彙；不同片段可能撞到同一桶。
# EXTRA_SYMBOLS 補括號、花括號、反引號等舊版未計數的 JavaScript 邊界訊號。
HASH_BUCKETS = 512
EXTRA_SYMBOLS = ['(', ')', '{', '}', '$', '`', '/', '\\', ':', '&', '#']
EXTRA_PATTERNS = [r'\b(?:alert|prompt|confirm|eval|Function|setTimeout|setInterval|void|console\.info|String\.fromCharCode)\s*\(',
                  r'\b(?:document|window|location)\s*\.', r'\$\{', r'["\'`]\s*;',
                  r'</(?:script|textarea|style|title)',
                  r'%(?:3c|3e|22|27|28|29|3b|24|7b|7d)',
                  r'(?:%3c\s*script|on\w+%3d|javascript%3a)',
                  r'&#(?:x[0-9a-f]+|\d+);|&(?:lt|gt|quot|apos);']


def raw_ngrams(value):
    # Callable analyzer avoids sklearn's built-in char whitespace compression.
    """逐個產生原字串的 2、3、4、5 字元連續片段，供 HashingVectorizer 使用。
    輸入 value 是字串；輸出是 generator，每次 yield 一段字串，而非一次建立全部片段清單。
    例如 abcd 的 2-gram 為 ab、bc、cd，3-gram 為 abc、bcd，4-gram 為 abcd；沒有 5-gram。
    size 控制片段長度，start 是起始字元位置；超出字串長度的 size 不產生片段。
    使用 callable analyzer，避免 sklearn 內建字元分析器把連續空白壓縮而改變原文。
    不做小寫化或 URL 解碼，因此 Ab 與 ab、%3C 與 < 可落入不同桶。
    """
    for size in range(2, 6):
        for start in range(max(0, len(value) - size + 1)):
            yield value[start:start + size]


# analyzer 自行產生原字元片段；norm=None 保留計數，alternate_sign=False 不用正負號抵消。
# lowercase=False 不改值的大小寫；此物件只做 transform，不會 fit 測試資料。
HASHER = HashingVectorizer(analyzer=raw_ngrams, n_features=HASH_BUCKETS,
                          norm=None, alternate_sign=False, lowercase=False)


def feature_count(header_names):
    """輸入 header_names 為固定具名 header 清單；輸出完整 v5 向量的整數維度。
    舊有部分是 74+17×N，保留 method、格式、query/body/path 訊號及具名 header 槽位。
    v5 對 query、body、path、headers 四個通道各追加 512 桶＋11 個符號數＋8 個正則數。
    當 N=12：74+17×12+4×(512+11+8)=2402，不是舊版 278。
    此公式必須與 features 的實際追加順序一致，推論端會拿它核對 metadata 和樹模型。
    """
    return 74 + 17 * len(header_names) + 4 * (HASH_BUCKETS + len(EXTRA_SYMBOLS) + len(EXTRA_PATTERNS))


def layout():
    """回傳可存入 metadata.json 的 v5 計算布局字典，不讀資料也不訓練詞彙表。
    channels 固定為 query、body、path、headers；每通道的設定含 512 桶與 2～5 字元片段。
    normalization=None 表示不將特徵向量做 L1/L2 正規化；lowercase_values=False 保留值大小寫。
    vocabulary_fit=False 表示不從 train 或測試資料建立詞彙表，雜湊規則事先固定。
    推論端比較完整 layout，避免只因維度相同就錯用另一套特徵。
    """
    return {'version': VERSION, 'hash_buckets_per_channel': HASH_BUCKETS,
            'ngram_sizes': [2, 3, 4, 5], 'channels': ['query', 'body', 'path', 'headers'],
            'normalization': None, 'lowercase_values': False, 'vocabulary_fit': False,
            'extra_symbols': EXTRA_SYMBOLS, 'extra_patterns': EXTRA_PATTERNS,
            'accept_sql_comment_policy': 'media-range-wildcard-v1'}


def clean(value):
    """輸入可為字典、清單、字串或其他值；輸出為依欄位名稱遮蔽憑證後的副本。
    這是 redact_fields 的相容入口，不會移除一般姓名、email、商品 ID 或攻擊符號。
    它不修改原物件，不送 HTTP，也不判斷輸入屬於哪一類攻擊。
    """
    return redact_fields(value)


def text(value):
    # A string is already input text, not an invitation to parse it again as JSON/form.
    """輸入 value：要統計文字訊號的值。輸出：一段字串。
    若輸入就是字串，原樣回傳；若是 dict/list/數字等，以 JSON 表示法轉為字串。
    例如 {'page': 2} 變成包含 page 與 2 的 JSON 文字，供 signals 統計長度與符號。
    ensure_ascii=False 讓中文字維持中文字，不變成多段反斜線 u 編碼而改變長度訊號。
    """
    return value if isinstance(value, str) else json.dumps(redact_fields(value), ensure_ascii=False)


def signals(value):
    # Ignore case for keyword counting only; never rewrite the stored input.
    """輸入 value 必須是字串；輸出是固定 16 格數值清單。
    第 0 格：Python 字串長度（字元數，不是 UTF-8 位元組數）。
    第 1～7 格：依序統計 %、單引號、雙引號、<、>、;、= 出現幾次。
    第 8～15 格：依 PATTERNS 順序統計邏輯關鍵字、union、select、sleep/benchmark、
    註解符號、script 標記、事件屬性、javascript: 等正則的命中數。

    例如 value="a'b"，前幾格會是 [3, 0, 1, 0, ...]：長度 3，百分號 0，單引號 1。
    這些是學習用訊號，不是「看見單引號就判定 SQLi」的封鎖規則。
    同一個單引號也可能出現在正常姓名，模型必須從資料學習其組合，並接受誤報評估。
    """
    return [len(value), *[value.count(c) for c in ['%', "'", '"', '<', '>', ';', '=']],
            *[len(re.findall(pattern, value, re.I)) for pattern in PATTERNS]]



# Accept的媒體型別語意只修正SQL註解那一格；原文、長度、符號與ngram完整保留。
_HTTP_TOKEN = r"[!#$%&'+.^_`|~0-9A-Za-z-]+"
_ACCEPT_ITEM = re.compile(r'\s*(?P<media>\*/\*|'+_HTTP_TOKEN+r'/(?:\*|'+_HTTP_TOKEN+r'))'
    r'(?:\s*;\s*'+_HTTP_TOKEN+r'\s*=\s*(?:'+_HTTP_TOKEN+r'|"(?:[^"\\\r\n]|\\[^\r\n])*"))*\s*(?:,|$)')


def accept_wildcard_comments(value):
    """只辨識完整可解析Accept清單中，媒體型別位置的合法萬用值。

    參數／引號內的/*不豁免；未知或畸形值不豁免。不是攻擊allowlist，
    更不直接決定normal標籤。只避免把HTTP格式本身算成SQL註解。
    """
    if isinstance(value,list):return sum(accept_wildcard_comments(v) for v in value)
    if not isinstance(value,str) or not value:return 0
    position=0;count=0
    while position<len(value):
        match=_ACCEPT_ITEM.match(value,position)
        if match is None or match.end()==position:return 0
        media=match.group('media')
        if media.endswith('/*'):count+=len(re.findall(PATTERNS[4],media))
        position=match.end()
        if value[:position].rstrip().endswith(',') and not value[position:].strip():return 0
    return count


def contextual_header_signals(name,value):
    result=signals(text(value))
    if str(name).lower()=='accept':result[12]-=accept_wildcard_comments(value)
    return result


def header_features(headers, header_names):
    """輸入 headers：一筆請求觀測到的 header 字典。
    輸入 header_names：訓練規格中排序後的具名 header 清單，不能任意改順序。
    輸出：18 + 17×len(header_names) 格數值。
    前 18 格是 header 總數、敏感 header 數與非敏感 header 整體文字的 16 格訊號。
    後面每個具名 header 都是 1 格存在旗標加 16 格值訊號。

    例如 schema 包含 x-locale，但這筆沒帶它，該槽 17 格全部為 0。
    若有 Authorization，存在旗標為 1，但它的 16 格值訊號為 0，避免學到 token 本身。
    文件未列出的普通 header 仍參與整體統計，只是沒有獨立的具名槽位。
    headers 中同名重複值的表示方式由輸入端決定；gateway 會先合併成模型副本字典。
    """
    observed = {str(k).lower(): v for k, v in headers.items()}
    ordinary = {k: v for k, v in headers.items() if not SENSITIVE.search(str(k))}
    aggregate=signals(text(ordinary))
    aggregate[12]-=sum(accept_wildcard_comments(v) for k,v in ordinary.items() if str(k).lower()=='accept')
    result = [len(headers), sum(bool(SENSITIVE.search(str(k))) for k in headers)] + aggregate
    # One named block for EACH header from the three API documents, not Content-Type only.
    for name in header_names:
        present = name in observed
        result.append(int(present))
        result += contextual_header_signals(name,observed[name]) if present and not SENSITIVE.search(name) else [0] * 16
    return result


def features(request, header_names=None):
    """輸入 request 是單筆模型請求副本；header_names 是訓練／推論共用的固定名稱順序。
    輸出普通數值清單，不讀 annotation、HTTP 回應、來源證據或正確答案。

    前段仍保留舊版布局：
    0～4：GET/POST/PUT/PATCH/DELETE 旗標；5～7：json/form/multipart 內容類型旗標。
    8～23：query 的 16 訊號；24～39：body；40～55：path；56～73：header 整體統計。
    74 起：每個具名 header 的 17 格（存在旗標＋16 文字訊號），合計 74+17×N 格。

    後段按 query、body、path、headers 的固定次序，每通道接上：
    11 格 EXTRA_SYMBOLS 計數 → 8 格 EXTRA_PATTERNS 命中數 → 512 格 n-gram 雜湊桶。
    N=12 時前段 278 格，後段每通道 531 格，完整為 2402 格。
    例如同樣長度、單引號數也相同的兩段文字，字元片段可能不同，能補充舊版統計看不出的差異。

    HASHER 不需要 fit，不從 test/validation 學詞彙；但固定 512 桶會有碰撞，
    不同片段甚至不同請求仍可能得到相同數值，不能保證每個攻擊寫法都能區分。
    分開通道避免 query 與 body 的相同片段被直接加在同一段向量。
    header_text 只含非敏感 header，名稱轉小寫再排序以穩定字典表示，值大小寫仍保留。
    raw_query/raw_body 有原文就優先使用；None 才退回解析結構，空字串不視為缺失。
    這裡沒有將百分比或 HTML entity 全部解碼；正則只統計部分可疑編碼寫法。
    """
    if header_names is None:
        from header_contracts import documented_headers
        header_names, _ = documented_headers()
    # 先套用訓練／推論共用遮蔽規則。憑證值不會進入統計或雜湊通道。
    request = prepare_request(request)
    headers = request['headers']
    content_type = next((str(v).lower() for k, v in headers.items() if k.lower() == 'content-type'), '')
    result = [int(request['method'].upper() == m) for m in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']]
    result += [int(t in content_type) for t in ['json', 'form', 'multipart']]
    # raw 是實際或離線明確提供的文字視角；None 才退回解析結構，不用 truthy 判斷空字串。
    query = request['raw_query'] if request['raw_query'] is not None else text(request['query'])
    body = request['raw_body'] if request['raw_body'] is not None else text(request['body'])
    for value in (query, body, request['path']):
        result += signals(value)
    result += header_features(headers, header_names)
    # Header names are case-insensitive identifiers; values are preserved verbatim.
    ordinary = {str(k).lower(): v for k, v in headers.items() if not SENSITIVE.search(str(k))}
    # 排序普通 header 名稱，避免字典插入順序改變雜湊；值與原編碼仍保留。
    header_text = json.dumps(ordinary, ensure_ascii=False, sort_keys=True)
    # 每通道按相同順序加特徵，不能在推論端交換 query/body 等位置。
    # transform([value]) 的形狀為 1×512；toarray()[0] 取一列，tolist 轉回普通 list。
    for value in (query, body, request['path'], header_text):
        result += [value.count(c) for c in EXTRA_SYMBOLS]
        result += [len(re.findall(pattern, value, re.I)) for pattern in EXTRA_PATTERNS]
        result += HASHER.transform([value]).toarray()[0].tolist()
    return result
