"""讀取 CSV/JSONL，依 live/offline 模式核對請求格式與可搬移 HTTP 證據。"""
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
from request_input import INPUT_VERSION, from_evidence, prepare_request


def read_rows(path):
    """輸入 path：CSV 或 JSONL 檔案路徑；輸出：完整樣本字典的 list。
    CSV 逐列讀「完整紀錄JSON」，不依賴 Excel 轉型後的顯示欄位。
    JSONL 則每一行解析為一個樣本，空行略過。
    支援帶 BOM 的 UTF-8，避免 Windows 匯出的第一個欄名多出不可見字元。
    若檔案不存在、JSON 破損或欄位缺漏，會讓例外往上交給 preflight 匯整。
    此函式不核對證據；讀得到資料不代表資料已完成 HTTP 執行。
    """
    path = Path(path)
    if path.suffix.lower() == '.csv':
        with path.open(encoding='utf-8-sig', newline='') as f:
            rows = [json.loads(r['完整紀錄JSON']) for r in csv.DictReader(f)]
    else:
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    for row in rows:
        if 'audit' in row and 'label' in row:
            audit = row['audit']
            row['metadata'] = dict(audit['metadata'])
        if 'label' in row:
            row['annotation'] = {**row.get('annotation', {}), 'label': row['label']}
    return rows


def check_evidence(row, evidence_root):
    """輸入 row：一筆完整資料；evidence_root：目前電腦上存放證據的根資料夾。
    正常完成回傳 None；任何核對失敗都拋 ValueError，不自動修改 row。

    例如來源是 sentinel/dataset/evidence/run-0.json，根目錄為 /workspace/MSDSS，
    就讀 /workspace/MSDSS/sentinel/dataset/evidence/run-0.json。
    到 Windows 可換成新的根目錄，metadata 仍保存同一條相對來源路徑。

    核對層次：路徑合法 → 位於允許的 reports/evidence 區 → 檔案 SHA 相符 →
    找到唯一 request_id → 平台與 HTTP 狀態一致 → 原始 target/body 可用 → 請求內容一致。
    即使只把 http_executed 改成 True，只要原文或證據不符，這裡仍會拒絕。
    只接受換行格式變化的 SHA 相容，不接受其他內容變更。
    """
    meta = row['metadata']
    # 將來源路徑轉為共用相對形式；拒絕絕對路徑、磁碟機與 ..，避免讀到私有設定。
    relative = PurePosixPath(str(meta.get('source_evidence', '')).replace('\\', '/'))
    if relative.is_absolute() or '..' in relative.parts or not relative.parts or ':' in str(relative):
        raise ValueError('證據路徑必須是相對路徑，不可含磁碟機或 ..')
    if not any(str(relative).startswith(prefix) for prefix in ('sentinel/local-platforms/reports/', 'sentinel/dataset/evidence/')):
        raise ValueError('證據只能來自已遮蔽 reports/evidence，不可讀取私有設定')
    root = Path(evidence_root).resolve()
    file = root.joinpath(*relative.parts).resolve()
    if not file.is_relative_to(root) or not file.is_file():
        raise ValueError('找不到來源證據；請提供 --evidence-root，不使用原電腦絕對路徑')
    raw = file.read_bytes()
    # 僅容許 Git/OS 造成的 LF/CRLF 換行差異；其他 bytes 變更仍不通過。
    lf = raw.replace(b'\r\n', b'\n')
    if meta.get('source_evidence_sha256') not in {hashlib.sha256(v).hexdigest() for v in (raw, lf, lf.replace(b'\n', b'\r\n'))}:
        raise ValueError('來源證據 SHA 不符')
    report = json.loads(raw)
    records = [r for r in report.get('requests', []) if r.get('request_id') == meta.get('request_id')]
    if (report.get('platform') != meta['platform'] or len(records) != 1
            or records[0].get('transport_error') or not isinstance(records[0].get('status'), int)
            or records[0]['status'] != meta.get('http_status')):
        raise ValueError('來源平台、request ID 或回應狀態不符')
    record = records[0]
    if 'request_target' not in record or record.get('request_body_raw') is None:
        raise ValueError('來源沒有實際原始 target／本文，不能只修改擷取旗標')
    # 核對完整模型副本而非只看旗標：CSV 所述輸入必須等於該次實際捕獲的請求。
    if from_evidence(record) != prepare_request(row['input']):
        raise ValueError('來源 HTTP 請求與訓練輸入內容不符')


def validate_rows(rows, split, exploratory=False, evidence_root=None, offline=False):
    """檢查單一集合的結構與來源條件；通過回傳 None，失敗拋 ValueError。
    rows 是完整樣本清單；split 為 train/test/validation 或存在時的 challenge。
    validation 平台限 Sylius；其他集合按目前規則要求 Bagisto 與 Shopware，排除 Medusa。
    exploratory 是較寬鬆的試跑開關，offline 則是明確允許生成資料的不同執行模式。

    共通檢查：集合不空、平台符合配置、metadata.split 與檔案名稱一致。
    offline=True 時要求 input 版本正確、pair_group 存在，以及 raw_query/raw_body 明確為字串。
    配對欄位避免把同一正常基底的攻擊變體拆散；字串可為空，但不能用 None 冒充已知原文。
    通過離線條件後 continue，刻意略過下方實測/session 證據條件，並非真的完成 HTTP。

    live 時仍拒絕 http_executed=False 或缺少真實 session_group。
    若 live 且不是 exploratory，再要求 http_executed=True、v3 擷取旗標與 check_evidence 逐筆核對。
    沒有人工核准門檻，也不依 http_status 是否 2xx 自動改標籤。
    即使本函式通過，仍可能有 normal 候選參數不合法或後端錯誤；不保證模型有效。
    """
    if not rows:
        raise ValueError(f'{split} 沒有資料')
    expected = {'sylius'} if split == 'validation' else {'bagisto', 'shopware'}
    if {r['metadata']['platform'] for r in rows} != expected:
        raise ValueError(f'{split} 平台必須為 {sorted(expected)}，不能混入 Medusa')
    for row in rows:
        meta = row['metadata']
        if meta.get('split') not in (None, split):
            raise ValueError('檔案集合與 metadata.split 不符')
        # offline 是另一條資料資格路徑，continue 會略過下方 HTTP/session 條件。
        # 離線模式仍保留 v3 格式、pair_group 與明確原文字串要求，不是毫無檢查。
        if offline:
            if meta.get('request_input_version') != INPUT_VERSION:
                raise ValueError('離線模式要求相同的 v3 原始輸入格式')
            if not meta.get('pair_group'):
                raise ValueError('離線變體必須保留 pair_group，不可隨機拆散正常／攻擊配對')
            request = row['input']
            if not isinstance(request.get('raw_query'), str) or not isinstance(request.get('raw_body'), str):
                raise ValueError('離線模式需明確的 raw_query／raw_body；不補造遺失原文')
            continue
        if meta.get('http_executed') is False:
            raise ValueError('包含未送出的候選計畫；請先實機採集，不能直接訓練')
        if not meta.get('session_group'):
            raise ValueError('缺少真實 session_group，不可用配對數冒充獨立流程數')
        # live 且非探索性時才逐筆核對實測證據；不含人工核准條件。
        if not exploratory:
            if meta.get('http_executed') is not True:
                raise ValueError('正式模式要求明確 http_executed=true')
            if meta.get('request_input_version') != INPUT_VERSION or not meta.get('raw_target_captured') or not meta.get('raw_body_captured'):
                raise ValueError('正式模式要求 v3 與實際擷取原文')
            if evidence_root is None:
                raise ValueError('正式模式需提供 --evidence-root 核對 HTTP 證據')
            check_evidence(row, evidence_root)
