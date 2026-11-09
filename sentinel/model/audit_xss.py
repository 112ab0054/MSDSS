"""Read-only XSS data/feature audit; optional fixed-parameter reproduction, no tuning."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import importlib.metadata
import itertools
import json
from pathlib import Path
import re
import sys
import numpy as np
from data_io import read_rows
import importlib.util

HERE = Path(__file__).resolve().parent
BASELINE = HERE/'history/xss-v4-baseline'
spec=importlib.util.spec_from_file_location('xss_features_v4_baseline',BASELINE/'features.py')
baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
features, signals, PATTERNS, LABELS, VERSION = baseline.features, baseline.signals, baseline.PATTERNS, baseline.LABELS, baseline.VERSION
SIGNALS = ['length', 'percent', 'single_quote', 'double_quote', 'lt', 'gt', 'semicolon', 'equals',
           'sql_logic', 'sql_union', 'sql_select', 'sql_delay', 'sql_comment', 'xss_script', 'xss_event', 'xss_url']
EXPECTED = {'test': [[21, 0, 7], [7, 21, 0], [18, 0, 10]],
            'validation': [[27, 0, 1], [8, 20, 0], [9, 3, 16]]}


def label(row):
    return row['annotation'].get('label', row['annotation'].get('proposed_label'))


def feature_names(headers):
    names = ['method.'+m for m in ['GET','POST','PUT','PATCH','DELETE']]
    names += ['content_type.'+m for m in ['json','form','multipart']]
    names += [location+'.'+s for location in ['query','body','path'] for s in SIGNALS]
    names += ['headers.count','headers.sensitive_count'] + ['headers.aggregate.'+s for s in SIGNALS]
    for header in headers:
        names += ['header.'+header+'.present'] + ['header.'+header+'.'+s for s in SIGNALS]
    return names


def write_csv(path, rows):
    if not rows:
        return
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def audit(data, output, reproduce=False):
    if output.exists():
        raise ValueError('輸出已存在，請另選新目錄')
    paths={s:data/(s+'.csv') for s in ['train','test','validation']}
    before={s:hashlib.sha256(p.read_bytes()).hexdigest() for s,p in paths.items()}
    sets={s:read_rows(p) for s,p in paths.items()}
    headers=json.loads((HERE/'header-schema.json').read_text(encoding='utf-8'))['header_names']
    names=feature_names(headers)
    vectors={s:np.asarray([features(r['input'],headers) for r in rows],dtype=np.float32) for s,rows in sets.items()}
    assert len(names)==vectors['train'].shape[1]
    xsig=[i for i,n in enumerate(names) if n.endswith(('.xss_script','.xss_event','.xss_url'))]
    indexes={s:{r['sample_id']:i for i,r in enumerate(rows)} for s,rows in sets.items()}
    normal_pairs={s:{r['metadata']['pair_group']:i for i,r in enumerate(rows) if label(r)=='normal'} for s,rows in sets.items()}
    report={'scope':'offline request classification; no HTTP or browser execution; no dataset/model changes',
            'feature_version':VERSION,'feature_count':len(names),'data_sha256':before,
            'source_sha256':{n:hashlib.sha256(((BASELINE if n!='audit_xss.py' else HERE)/n).read_bytes()).hexdigest() for n in ['features.py','request_input.py','audit_xss.py']},
            'splits':{}}
    details=[]
    for s,rows in sets.items():
        xrows=[r for r in rows if label(r)=='xss']
        payloads=Counter(r['metadata']['payload']['value'] for r in xrows)
        families=Counter((r['metadata']['payload'].get('family') or 'external_unclassified') for r in xrows)
        stats={'rows':len(xrows),'unique_payloads':len(payloads),'families':dict(families),
               'locations':dict(Counter(r['metadata']['target_location'] for r in xrows)),
               'payload_counts':[{'value':v,'rows':n} for v,n in payloads.most_common()]}
        for r in xrows:
            i=indexes[s][r['sample_id']]
            m=r['metadata'];payload=m['payload']['value']
            control=normal_pairs[s][m['pair_group']]
            delta=vectors[s][i]-vectors[s][control]
            source=signals(payload)[-3:]
            visible=bool(np.any(delta[xsig]>0))
            details.append({'split':s,'sample_id':r['sample_id'],'platform':m['platform'],
                'api':m['operation_path'],'location':m['target_location'],'parameter':m['target_parameter'],
                'family':m['payload'].get('family') or 'external_unclassified','payload':payload,
                'source_has_xss_pattern':bool(any(source)),'added_xss_pattern_in_full_vector':visible,
                'changed_feature_count':int(np.count_nonzero(delta)),
                'control_same_full_vector':not bool(np.any(delta)),
                'changed_feature_names':json.dumps([names[j] for j in np.flatnonzero(delta)],ensure_ascii=False)})
        current=[d for d in details if d['split']==s]
        stats['source_with_xss_pattern']=sum(d['source_has_xss_pattern'] for d in current)
        stats['full_request_with_added_xss_pattern']=sum(d['added_xss_pattern_in_full_vector'] for d in current)
        stats['source_pattern_lost_after_embedding']=sum(d['source_has_xss_pattern'] and not d['added_xss_pattern_in_full_vector'] for d in current)
        normal_indices=[i for i,r in enumerate(rows) if label(r)=='normal']
        stats['normal_controls_with_xss_specific_pattern']=sum(bool(np.any(vectors[s][i,xsig]>0)) for i in normal_indices)
        report['splits'][s]=stats
    # Distinct raw requests can still map to the exact same statistics.
    collisions=[]
    buckets=defaultdict(list)
    for s,rows in sets.items():
        for i,r in enumerate(rows):buckets[tuple(vectors[s][i])].append((s,r))
    for members in buckets.values():
        if len(members)<2:continue
        splits={s for s,r in members};labels={label(r) for s,r in members}
        if len(splits)>1 or len(labels)>1:
            collisions.append({'splits':';'.join(sorted(splits)),'labels':';'.join(sorted(labels)),
                'rows':len(members),'sample_ids':';'.join(r['sample_id'] for s,r in members),
                'mixed_labels':len(labels)>1})
    report['feature_collisions']={'groups':len(collisions),'mixed_label_groups':sum(c['mixed_labels'] for c in collisions)}
    # A context-conditioned JS-template input and ordinary text have identical current features.
    probe_a={'method':'POST','path':'/products','headers':{'Content-Type':'application/json'},
             'raw_query':'','body':{'note':'${void(0)}'},'raw_body':'{"note":"${void(0)}"}'}
    probe_b={**probe_a,'body':{'note':'blue shirt'},'raw_body':'{"note":"blue shirt"}'}
    report['controlled_collision']={'payload_a':'${void(0)}','payload_b':'blue shirt',
        'full_vector_identical':features(probe_a,headers)==features(probe_b,headers),
        'interpretation':'The first is an XSS-intent catalog string needing JS-template context, not proof of a browser exploit.'}
    normal_flags=[]
    for s,rows in sets.items():
        for i,r in enumerate(rows):
            if label(r)!='normal':continue
            query=r['input'].get('raw_query') or ''
            matches=re.findall(PATTERNS[-2],query,re.I)
            if matches:
                normal_flags.append({'split':s,'sample_id':r['sample_id'],'api':r['metadata']['operation_path'],
                                     'event_regex_matches_in_normal_query':matches})
    report['normal_query_event_pattern_matches']=normal_flags
    if reproduce:
        from xgboost import XGBClassifier
        from sklearn.metrics import confusion_matrix, accuracy_score
        y={s:np.array([LABELS.index(label(r)) for r in rows]) for s,rows in sets.items()}
        model=XGBClassifier(n_estimators=150,max_depth=3,learning_rate=.05,objective='multi:softprob',
            num_class=3,eval_metric='mlogloss',tree_method='hist',device='cpu',n_jobs=2,random_state=42)
        model.fit(vectors['train'],y['train'],verbose=False)
        report['reproduction']={'packages':{n:importlib.metadata.version(n) for n in ['numpy','scikit-learn','xgboost']},
                                'parameters_unchanged':True,'used_holdout_for_tuning':False,'results':{}}
        for s,rows in sets.items():
            probs=model.predict_proba(vectors[s]);pred=probs.argmax(axis=1)
            matrix=confusion_matrix(y[s],pred,labels=[0,1,2]).tolist()
            report['reproduction']['results'][s]={'confusion_matrix':matrix,'accuracy':float(accuracy_score(y[s],pred)),
                'matches_user_colab_matrix':matrix==EXPECTED[s] if s in EXPECTED else None}
            predicted={r['sample_id']:(LABELS[int(pred[i])],float(probs[i,0]),float(probs[i,2])) for i,r in enumerate(rows)}
            for d in details:
                if d['split']==s:
                    d['predicted'],d['p_normal'],d['p_xss']=predicted[d['sample_id']]
        order=np.argsort(model.feature_importances_)[::-1]
        report['reproduction']['top_features']=[{'name':names[i],'importance':float(model.feature_importances_[i])}
            for i in order[:15] if model.feature_importances_[i]>0]
        report['reproduction']['importance_by_block']={block:float(sum(model.feature_importances_[i] for i,n in enumerate(names) if n.startswith(block+'.')))
            for block in ['method','content_type','query','body','path','headers','header']}
        report['reproduction']['xss_predictions_by_location']={s:{loc:dict(Counter(d['predicted'] for d in details if d['split']==s and d['location']==loc))
            for loc in sorted({d['location'] for d in details if d['split']==s})} for s in sets}
    # Make a rectangular CSV even when reproduction is disabled.
    for d in details:
        for key in ('predicted','p_normal','p_xss'):d.setdefault(key,None)
    assert before=={s:hashlib.sha256(p.read_bytes()).hexdigest() for s,p in paths.items()}
    output.mkdir(parents=True)
    write_csv(output/'xss-samples.csv',details)
    write_csv(output/'feature-collisions.csv',collisions)
    (output/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# XSS 資料涵蓋與特徵辨識診斷','', '日期：2026-11-09。只讀資料；沒有修改特徵、原文、分割、參數或部署模型。',
           '本次為離線分類診斷，不發送 HTTP、不執行瀏覽器腳本；家族名稱是生成意圖，不代表漏洞成立。','',
           '| 集合 | XSS 筆數 | 不同 payload 原文 | 原文命中 XSS 專用模式 | 嵌入請求後新增專用訊號 | 原訊號消失 |',
           '|---|---:|---:|---:|---:|---:|']
    for s,st in report['splits'].items():
        lines.append(f'| {s} | {st["rows"]} | {st["unique_payloads"]} | {st["source_with_xss_pattern"]} | {st["full_request_with_added_xss_pattern"]} | {st["source_pattern_lost_after_embedding"]} |')
    lines+=['','## 家族與位置差異','']
    for s,st in report['splits'].items():
        lines += [f'- {s}：家族 `{json.dumps(st["families"],ensure_ascii=False)}`；位置 `{json.dumps(st["locations"],ensure_ascii=False)}`。']
    lines+=['','訓練只有 script／event／URL 類；test 刻意保留 JS 字串／模板家族。這是未見家族、不同 API 與位置分布共同改變的測試，不能當成純粹隨機同分布測試。',
       'validation 原資料未提供本地 family 欄，external_unclassified 是缺少這份分類資訊，不等於沒有家族或只有一種。',
       '沒有 HTTP／儲存讀回／瀏覽器執行證據，因此本次不能確認反射型、儲存型或 DOM-XSS 的行為覆蓋；以上只量測請求可見的字串與來源家族。',
       '', '## 具體辨識盲點','',
       '目前每段文字只有 16 項統計，XSS 專用模式只有 `<script`、`on…=`、`javascript:`；不計括號、反引號、美元符、花括號、`//`、`alert`、`void` 或屬性／JS 語境。',
       f'相同請求框架中，`${{void(0)}}` 與 `blue shirt` 的完整 278 維特徵相同：{report["controlled_collision"]["full_vector_identical"]}。原文字串仍不同，這是特徵資訊不足，不是把資料正規化。',
       'Query／Path 的必要傳輸編碼會把 `<`、`=`、`:` 等變成百分比字樣，原文 regex 不能直接看到；上表用正常配對作差，實際量測專用訊號是否消失。沒有解碼或改寫輸入。',
       f'正常 Query 被 event regex 命中的紀錄數：{len(normal_flags)}；具體符合片段見 audit.json。這是特徵誤匹配，不必然等同模型誤判的因果證明。',
       f'跨集合或跨標籤相同向量群：{len(collisions)}；其中混合標籤群：{report["feature_collisions"]["mixed_label_groups"]}。共用向量群不是原始請求重複筆數，見 feature-collisions.csv。',
       f'訓練 normal 對照中，命中目前三種 XSS 專用模式的筆數：{report["splits"]["train"]["normal_controls_with_xss_specific_pattern"]}。若為 0，沒有檢查到可要求模型區分「看似 XSS 但合法」的這類正常對照；不能僅靠關鍵字共現宣稱語意辨識。']
    if reproduce:
        lines+=['','## 固定參數重現','', '使用目前程式相同的 150 棵樹、深度 3、seed=42；只 fit train，沒有用 test／validation 選參數。以下是本機重現，不冒充取得 Colab 逐筆預測檔。','',
                '```json',json.dumps(report['reproduction'],ensure_ascii=False,indent=2),'```','',
                '### XSS 原文與本機預測分布','', '| 集合 | Payload 原文（JSON 字串） | 筆數 | 預測 normal | 預測 sqli | 預測 xss |','|---|---|---:|---:|---:|---:|']
        for s in sets:
            grouped=defaultdict(list)
            for d in details:
                if d['split']==s:grouped[d['payload']].append(d)
            for value,ds in grouped.items():
                safe=json.dumps(value,ensure_ascii=False).replace('|','\\|').replace('<','&lt;').replace('>','&gt;')
                counts=Counter(d['predicted'] for d in ds)
                lines.append(f'| {s} | `{safe}` | {len(ds)} | {counts["normal"]} | {counts["sqli"]} | {counts["xss"]} |')
    lines+=['','## 建議修正方向（本次未實作）','',
      '1. 保留這次基準與分割。將「已見家族的新請求」及「未見家族」設為不同實驗，不能為提高 test 分數把考題加回 train。',
      '2. 在 train 內補齊有來源的 JS 字串／模板、不同編碼與位置、及合法程式碼文字／特殊符號的正常對照；各家族需多個獨立基底，不靠換尾數或同一 payload 套很多 API 湊數。',
      '3. 不正規化原文；考慮新增原字元的字元 n-gram、JS 邊界符號與百分比編碼字樣特徵。詞彙與任何選擇只 fit train；關鍵字本身不證明攻擊，須搭配正常對照。',
      '4. 採用受控的 train 內分組比較，再固定新版本。已看過的 test／Sylius 成績不能作反覆調參的依據；最終效果另保留新資料。',
      '5. 附有 cmd／SSI、外部腳本 URL 或極短片段的外部樣本需查核語境與三分類標籤適用性；本次不執行、不自動改標籤。',
      '', '完整逐筆結果：xss-samples.csv；來源 SHA、訊號統計與重現資訊：audit.json。']
    (output/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',type=Path,default=HERE.parent/'dataset/small-api-v2')
    p.add_argument('--output',type=Path,default=HERE/'xss-audit-2026-11-09')
    p.add_argument('--reproduce',action='store_true')
    a=p.parse_args();r=audit(a.data_dir,a.output,a.reproduce)
    print(json.dumps({'output':str(a.output),'splits':r['splits'],'collisions':r['feature_collisions'],
                      'reproduction':r.get('reproduction',{}).get('results')},ensure_ascii=False))
