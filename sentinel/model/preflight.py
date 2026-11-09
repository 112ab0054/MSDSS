"""訓練前只讀檢查：固定分割、資格與洩漏；不改標籤、不訓練模型。"""
from collections import Counter
import hashlib
import json
import itertools
import numpy as np
from data_io import read_rows, validate_rows
from features import LABELS


def inspect_dataset(data_dir, group_function, exploratory=False, evidence_root=None, header_schema=None, offline=False):
    """一次檢查固定集合、來源、分組與新版 v3 實驗規則，不訓練、不修標籤或重新洗牌。
    輸入 data_dir 是資料目錄；group_function 是分組函式；offline/exploratory 決定來源檢查模式。
    header_schema 用於文件指紋比對，evidence_root 決定目前電腦上的證據根目錄。
    回傳五個值：sets（各集合樣本）、all_rows（暫時串接清單）、indices（各集合位置）、
    group（每列關聯群）、report（含 ready/errors/warnings 的摘要）。
    串接 all_rows 只為發現跨集合關聯，不把 validation 或 challenge 加入 train。

    先讀 train/test/validation，若存在 challenge.csv 再加進來。任何集合仍須包含三類。
    observed_sessions 統計真實標記的 session，pair_groups 統計配對，不能混稱實測流程數。
    用 group_function 一起分組，再比較所有集合組合的群組交集，包括 challenge。
    errors 累積問題；ready 代表既有檢查沒有報錯，不代表資料充足或模型成績可靠。

    當 provenance 指定 document-v3-seen-families-heldout-templates 時：
    1. 每列的 evaluation_protocol 必須一致，避免混入另一種實驗設計。
    2. 一般 test 的攻擊家族必須是 train 家族的子集；未知家族應放 challenge。
    3. challenge 家族不得與 train/test 重疊，維持未知家族考題的定義。
    4. 任兩集合不得有完全相同的 payload.value 攻擊原文。
    5. 模板、配對、來源及 session 的關聯仍由 groups 檢查，不因允許見過家族而全部解除。
    這不等於已自動辨識所有語意相近模板，也不保證 validation 家族一律與 train 不同。

    v4 改用 skeletons.audit_dataset 重算完整目錄與實際原文，禁止跨集合骨架；家族可共享。
    骨架分析只產生輔助分組，不改寫模型輸入，不是完整語意等價證明。

    文件核對容許 LF/CRLF 差異；找不到文件標 not_available，目前不因此一律報錯。
    資料列宣稱使用 v3 協議卻缺 provenance 時會報錯，不能只改模式字串繞過規則。
    offline 的 warnings 會明確說明沒有完成平台 HTTP，group 數也不是購物流程數。
    """
    sets, summary, errors = {}, {}, []
    split_names=['train','test','validation']
    # 四集合各有用途，challenge 缺席就不檢查；存在則連同其他集合一起比對關聯。
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
                'attack_skeleton_groups': {label:len({r['metadata'].get('skeleton_group_id') for r in rows if r['annotation'].get('label',r['annotation'].get('proposed_label'))==label and r['metadata'].get('skeleton_group_id')}) for label in ('sqli','xss')},
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
    # 暫時串接只用來找跨集合群組；indices 保存每個集合對應的位置。
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
        # 比較所有兩兩組合，包括 train/challenge、validation/challenge，不只比較 train/test。
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
        # v3 的 seen-family 規則只在明確宣告此協議時啟用，不能套到所有歷史資料。
        if saved.get('evaluation_protocol') == 'document-v3-seen-families-heldout-templates':
            for split,rows in sets.items():
                if any(r['metadata'].get('evaluation_protocol')!=saved['evaluation_protocol'] for r in rows):
                    errors.append('資料列與來源記錄的實驗規則不符：'+split)
            def family_set(split):
                return {r['metadata']['payload']['family'] for r in sets.get(split,[])
                        if r['metadata'].get('payload') and r['metadata']['payload'].get('family')}
            # <= 是集合子集關係：一般 test 不能包含 train 未見的家族。
            if not family_set('test')<=family_set('train'):
                errors.append('一般 test 含 train 未見家族，應放 challenge')
            # & 是集合交集：challenge 的家族不得與 train/test 重疊。
            if family_set('challenge') & (family_set('train')|family_set('test')):
                errors.append('challenge 家族與 train/test 重疊')
            for left,right in itertools.combinations(sets,2):
                # 比較各集合 payload 的完整原文，避免只是換 API/session 就把同一句攻擊當新考題。
                values=lambda s:{r['metadata']['payload']['value'] for r in sets[s] if r['metadata'].get('payload')}
                if values(left)&values(right):errors.append(f'{left}/{right} 攻擊原文重複')
        elif saved.get('evaluation_protocol') == 'document-v4-skeleton-disjoint':
            from skeletons import audit_dataset
            errors.extend(audit_dataset(data_dir,sets,saved))
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
    if any(r['metadata'].get('evaluation_protocol')=='document-v4-skeleton-disjoint' for r in all_rows) and (not provenance.exists() or saved.get('evaluation_protocol')!='document-v4-skeleton-disjoint'):
        errors.append('v4 骨架實驗必須附上對應 provenance.json')
    report = {'ready': not errors, 'mode': 'offline' if offline else 'live', 'exploratory': bool(exploratory or offline), 'splits': summary,
              'document_snapshots': snapshots, 'errors': errors,
              'warnings': ['離線生成資料：可評估分類器，但沒有完成平台 HTTP 實機驗證。群組數是相依關聯的合併結果，不等於真實購物流程數。'] if offline else [],
              'note': '檢查通過僅代表目前程式的資格與分組條件通過，不代表模型有效。'}
    return sets, all_rows, indices, group, report
