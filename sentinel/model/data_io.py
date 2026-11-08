"""Portable split loading and evidence checks; no repository-location assumptions."""
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
from request_input import INPUT_VERSION, from_evidence, prepare_request


def read_rows(path):
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
            row['metadata']['training_approved'] = audit.get('review_status') == 'approved'
            row['annotation'] = {'label': row['label']}
    return rows


def check_evidence(row, evidence_root):
    meta = row['metadata']
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
    if from_evidence(record) != prepare_request(row['input']):
        raise ValueError('來源 HTTP 請求與訓練輸入內容不符')


def validate_rows(rows, split, exploratory=False, evidence_root=None):
    if not rows:
        raise ValueError(f'{split} 沒有資料')
    expected = {'sylius'} if split == 'validation' else {'bagisto', 'shopware'}
    if {r['metadata']['platform'] for r in rows} != expected:
        raise ValueError(f'{split} 平台必須為 {sorted(expected)}，不能混入 Medusa')
    for row in rows:
        meta = row['metadata']
        if meta.get('split') not in (None, split):
            raise ValueError('檔案集合與 metadata.split 不符')
        if meta.get('http_executed') is False:
            raise ValueError('包含未送出的候選計畫；請先實機採集，不能直接訓練')
        if not meta.get('session_group'):
            raise ValueError('缺少真實 session_group，不可用配對數冒充獨立流程數')
        if not exploratory:
            if not meta.get('training_approved') or meta.get('http_executed') is not True:
                raise ValueError('正式模式要求明確人工核准與 http_executed=true')
            if meta.get('request_input_version') != INPUT_VERSION or not meta.get('raw_target_captured') or not meta.get('raw_body_captured'):
                raise ValueError('正式模式要求 v3 與實際擷取原文')
            if evidence_root is None:
                raise ValueError('正式模式需提供 --evidence-root 核對 HTTP 證據')
            audit = row.get('audit', {})
            if (audit.get('review_status') != 'approved' or not str(audit.get('reviewer', '')).strip()
                    or not str(audit.get('reason', '')).strip() or len(audit.get('candidate_sha256', '')) != 64):
                raise ValueError('正式模式僅接受含審核人、理由與候選 SHA 的審核匯出')
            check_evidence(row, evidence_root)
