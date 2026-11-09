"""訓練前只讀檢查：固定分割、資格與洩漏；不改標籤、不訓練模型。"""
from collections import Counter
import hashlib
import json
import itertools
import numpy as np
from data_io import read_rows, validate_rows
from features import LABELS


def inspect_dataset(data_dir, group_function, exploratory=False, evidence_root=None, header_schema=None, offline=False):
    """一次列出三個集合的問題，避免到 Colab 才逐次碰到第一個錯誤。"""
    sets, summary, errors = {}, {}, []
    split_names=['train','test','validation']
    if (data_dir/'challenge.csv').is_file():split_names.append('challenge')
    for split in split_names:
        path = data_dir / (split + '.csv')
        try:
            rows = read_rows(path)
            sets[split] = rows
            labels = Counter(r['annotation'].get('label', r['annotation'].get('proposed_label')) for r in rows)
            summary[split] = {
                'rows': len(rows), 'labels': dict(labels),
                'platforms': dict(Counter(r['metadata']['platform'] for r in rows)),
                'http_executed': sum(r['metadata'].get('http_executed') is True for r in rows),
                'observed_sessions': len({r['metadata']['session_group'] for r in rows if r['metadata'].get('session_group')}),
                'pair_groups': len({r['metadata']['pair_group'] for r in rows if r['metadata'].get('pair_group')}),
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            if set(labels) != set(LABELS):
                errors.append(f'{split} 必須包含 normal/sqli/xss，且不能有其他標籤')
            try:
                validate_rows(rows, split, exploratory, evidence_root, offline=offline)
            except ValueError as error:
                errors.append(f'{split}: {error}')
        except (OSError, ValueError, KeyError, TypeError) as error:
            errors.append(f'{split}: 無法讀取資料（{type(error).__name__}）')
    indices, all_rows = {}, []
    for split, rows in sets.items():
        indices[split] = np.arange(len(all_rows), len(all_rows) + len(rows))
        all_rows.extend(rows)
    group = np.array([], dtype=int)
    try:
        ids = [r.get('sample_id') for r in all_rows]
        if any(not sid for sid in ids) or len(ids) != len(set(ids)):
            errors.append('樣本 ID 缺失或跨集合重複')
        group = group_function(all_rows)
        for split in sets:
            summary[split]['independent_groups'] = len(set(group[indices[split]]))
        for left, right in itertools.combinations(sets,2):
            if left in indices and right in indices and set(group[indices[left]]) & set(group[indices[right]]):
                errors.append(f'{left}/{right} 有來源／session／配對／家族／重複群交集；不可重新洗牌解決')
    except (KeyError, TypeError, ValueError) as error:
        errors.append(f'分組欄位不完整：{type(error).__name__}')
    # v2 使用來源快照；能找到原專案時額外核對，不將雜湊改成目前值。
    provenance = data_dir / 'provenance.json'
    snapshots = {}
    if provenance.exists():
        saved = json.loads(provenance.read_text(encoding='utf-8-sig'))
        if saved.get('evaluation_protocol') == 'document-v3-seen-families-heldout-templates':
            for split,rows in sets.items():
                if any(r['metadata'].get('evaluation_protocol')!=saved['evaluation_protocol'] for r in rows):
                    errors.append('資料列與來源記錄的實驗規則不符：'+split)
            def family_set(split):
                return {r['metadata']['payload']['family'] for r in sets.get(split,[])
                        if r['metadata'].get('payload') and r['metadata']['payload'].get('family')}
            if not family_set('test')<=family_set('train'):
                errors.append('一般 test 含 train 未見家族，應放 challenge')
            if family_set('challenge') & (family_set('train')|family_set('test')):
                errors.append('challenge 家族與 train/test 重疊')
            for left,right in itertools.combinations(sets,2):
                values=lambda s:{r['metadata']['payload']['value'] for r in sets[s] if r['metadata'].get('payload')}
                if values(left)&values(right):errors.append(f'{left}/{right} 攻擊原文重複')
        elif any(r['metadata'].get('evaluation_protocol')=='document-v3-seen-families-heldout-templates' for r in all_rows):
            errors.append('v3 實驗規則必須附上對應 provenance.json')
        for name, expected in saved.get('parameter_document_sha256', {}).items():
            if header_schema is not None and header_schema.get('document_sha256', {}).get(name) != expected:
                errors.append('Header schema 與資料來源文件快照不符：' + name)
            if evidence_root is None:
                snapshots[name] = 'not_available'
                continue
            path = (evidence_root / name).resolve()
            if not path.is_relative_to(evidence_root.resolve()):
                errors.append('來源文件路徑超出 evidence-root')
                continue
            if path.is_file():
                raw = path.read_bytes()
                lf = raw.replace(b'\r\n', b'\n')
                matched = expected in {hashlib.sha256(v).hexdigest() for v in (raw, lf, lf.replace(b'\n', b'\r\n'))}
                snapshots[name] = 'match' if matched else 'mismatch'
                if not matched:
                    errors.append('API 文件與資料來源快照不符：' + name)
            else:
                snapshots[name] = 'not_available'
    if not provenance.exists() and any(r['metadata'].get('evaluation_protocol')=='document-v3-seen-families-heldout-templates' for r in all_rows):
        errors.append('v3 實驗規則必須附上對應 provenance.json')
    report = {'ready': not errors, 'mode': 'offline' if offline else 'live', 'exploratory': bool(exploratory or offline), 'splits': summary,
              'document_snapshots': snapshots, 'errors': errors,
              'warnings': ['離線生成資料：可評估分類器，但沒有完成平台 HTTP 實機驗證。群組數是相依關聯的合併結果，不等於真實購物流程數。'] if offline else [],
              'note': '檢查通過僅代表目前程式的資格與分組條件通過，不代表模型有效。'}
    return sets, all_rows, indices, group, report
