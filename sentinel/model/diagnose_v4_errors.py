"""凍結v4誤判診斷：核對逐筆預測、文件欄位與特徵敏感度；不改資料或正式訓練入口。"""
import argparse
from collections import Counter, defaultdict
import copy
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import sys
import numpy as np
from xgboost import XGBClassifier, DMatrix
from data_io import read_rows
from features import features, signals, LABELS, VERSION, EXTRA_PATTERNS, EXTRA_SYMBOLS
from header_contracts import documented_headers

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'sentinel/dataset'))
from build_small_dataset import read_documents, field_value, finalize
from build_xss_v3 import set_field


def label(row):
    return row['annotation'].get('label',row['annotation'].get('proposed_label'))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path,rows):
    if not rows:return
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def focus(actual,predicted):
    if actual=='sqli' and predicted=='normal':return 'SQLi漏判為正常'
    if actual=='sqli' and predicted=='xss':return 'SQLi混淆為XSS'
    if actual=='normal' and predicted=='xss':return '正常誤報為XSS'
    return ''


def names(headers):
    basic=['length','percent','single_quote','double_quote','lt','gt','semicolon','equals','sql_logic','sql_union','sql_select','sql_delay','sql_comment','xss_script','xss_event','xss_url']
    result=['method.'+m for m in ['GET','POST','PUT','PATCH','DELETE']]+['content_type.'+m for m in ['json','form','multipart']]
    for loc in ('query','body','path'):result += [loc+'.'+n for n in basic]
    result += ['headers.count','headers.sensitive_count']+['headers.aggregate.'+n for n in basic]
    for h in headers:result += ['header.'+h+'.present']+['header.'+h+'.'+n for n in basic]
    for loc in ('query','body','path','headers'):
        result += [loc+'.symbol.'+repr(n) for n in EXTRA_SYMBOLS]
        result += [loc+'.extra_regex.'+str(i) for i in range(len(EXTRA_PATTERNS))]
        result += [loc+'.hash_bucket.'+str(i) for i in range(512)]
    return result


def diagnose(data,results,output):
    if output.exists():raise ValueError('請指定新的診斷輸出目錄，避免覆寫紀錄')
    paths={s:data/(s+'.csv') for s in ('train','test','validation','challenge')}
    before={s:sha(p) for s,p in paths.items()}
    sets={s:read_rows(p) for s,p in paths.items()}
    headers,doc_hashes=documented_headers();ops,_=read_documents()
    # Parameters remain exactly the predeclared v4 baseline; only train is fitted.
    model=XGBClassifier(n_estimators=150,max_depth=3,learning_rate=.05,objective='multi:softprob',num_class=3,
                        eval_metric='mlogloss',tree_method='hist',device='cpu',n_jobs=2,random_state=42)
    matrices={s:np.asarray([features(r['input'],headers) for r in rows],dtype=np.float32) for s,rows in sets.items()}
    model.fit(matrices['train'],np.array([LABELS.index(label(r)) for r in sets['train']]),verbose=False)
    predictions={s:model.predict_proba(x) for s,x in matrices.items()}
    prediction_sha={};max_error=0.
    for s in ('test','validation','challenge'):
        path=results/s/'predictions.csv';prediction_sha[s]=sha(path)
        with path.open(encoding='utf-8-sig',newline='') as f:cached={r['sample_id']:r for r in csv.DictReader(f)}
        if len(cached)!=len(sets[s]):raise ValueError('預測筆數與資料不符：'+s)
        for i,row in enumerate(sets[s]):
            saved=cached[row['sample_id']];actual=label(row);predicted=LABELS[int(predictions[s][i].argmax())]
            error=max(abs(float(saved['p_'+l])-float(predictions[s][i,j])) for j,l in enumerate(LABELS))
            max_error=max(max_error,error)
            if saved['actual']!=actual or saved['predicted']!=predicted or error>1e-6:
                raise ValueError('重現模型與既有逐筆預測不同，停止解讀：'+s)
    feature_names=names(headers)
    assert len(feature_names)==matrices['train'].shape[1]==2402 and VERSION==5
    comment_indices=[i for i,n in enumerate(feature_names) if n.endswith('.sql_comment')]
    details=[];probes=[];buckets=defaultdict(list)
    train_path_median=float(np.median([matrices['train'][i,40] for i,r in enumerate(sets['train']) if label(r)=='normal']))
    by_sample={};normal_indexes={}
    for s,rows in sets.items():
        by_sample[s]={r['sample_id']:r for r in rows}
        normal_indexes[s]={r['metadata']['pair_group']:i for i,r in enumerate(rows) if label(r)=='normal'}
        paired={r['metadata']['pair_group']:r for r in rows if label(r)=='sqli'}
        for i,r in enumerate(rows):
            m=r['metadata'];payload=m.get('payload') or {};actual=label(r)
            predicted=LABELS[int(predictions[s][i].argmax())]
            key=m['platform'],r['input']['method'],m['operation_path'];op=ops[key]
            loc=m.get('target_location');parameter=m.get('target_parameter');benign=m.get('benign_content_context')
            if actual=='normal' and benign:
                matches=[(l,n) for l,n in op['fields'] if n!='（本文）' and field_value(r['input'],l,n)==(True,benign['value'])]
                if len(matches)!=1:raise ValueError('正常文字定位不唯一：'+r['sample_id'])
                loc,parameter=matches[0]
            spec=op['fields'].get((loc,parameter),{})
            delta=matrices[s][i]-matrices[s][normal_indexes[s][m['pair_group']]]
            entry={'split':s,'sample_id':r['sample_id'],'actual':actual,'predicted':predicted,
                   'focus':focus(actual,predicted) if s!='train' else '',
                   'platform':m['platform'],'method':r['input']['method'],'api':m['operation_path'],
                   'location':loc,'parameter':parameter,'paired_injection_location':paired[m['pair_group']]['metadata']['target_location'],
                   'document_type':spec.get('type'),'document_meaning':spec.get('meaning'),
                   'document_values':spec.get('values'),'document':spec.get('source'),'document_line':spec.get('line'),
                   'family':payload.get('family') or ('external_unclassified' if payload else ''),
                   'skeleton_group':m.get('skeleton_group_id'),'payload':payload.get('value'),
                   'benign_literal':benign.get('value') if benign else None,
                   'payload_sql_comment_signal':bool(payload and signals(payload['value'])[12]),
                   'added_comment_feature':bool(np.any(delta[comment_indices]>0)),
                   'changed_features_vs_normal_pair':int(np.count_nonzero(delta)),
                   **{'p_'+l:float(predictions[s][i,j]) for j,l in enumerate(LABELS)}}
            details.append(entry)
            if s!='train':
                buckets[s,'family',actual,entry['family'] or ('benign_literal' if benign else 'document_baseline')].append(entry)
                buckets[s,'location',actual,loc or entry['paired_injection_location']].append(entry)
            # Counterfactual probes change in-memory copies only. They are not dataset rows or valid exploits.
            variants=[]
            if actual=='sqli':
                value=payload['value']
                if '--' in value:variants.append(('remove_double_dash_suffix',value.split('--',1)[0]))
                if not entry['payload_sql_comment_signal']:variants.append(('append_double_dash',value+' -- '))
            if actual=='normal' and benign:
                variants += [('neutral_ascii_same_char_length','N'*len(benign['value'])),
                             ('neutral_cjk_same_char_length','字'*len(benign['value']))]
            for probe,value in variants:
                req=copy.deepcopy(r['input']);set_field(req,loc,parameter,value);finalize(req,m['operation_path'])
                probs=model.predict_proba([features(req,headers)])[0]
                new_predicted=LABELS[int(probs.argmax())]
                probes.append({'split':s,'sample_id':r['sample_id'],'actual':actual,'probe':probe,
                               'location':loc,'parameter':parameter,'before_predicted':predicted,'after_predicted':new_predicted,
                               'before_value':payload.get('value') if payload else benign['value'],'after_value':value,
                               **{'before_p_'+l:float(predictions[s][i,j]) for j,l in enumerate(LABELS)},
                               **{'after_p_'+l:float(probs[j]) for j,l in enumerate(LABELS)}})
            if s!='train' and actual=='normal':
                vec=matrices[s][i].copy();vec[40]=train_path_median
                probs=model.predict_proba([vec])[0]
                probes.append({'split':s,'sample_id':r['sample_id'],'actual':actual,'probe':'path_length_feature_only',
                               'location':'path','parameter':'diagnostic vector index 40 only; raw path unchanged',
                               'before_predicted':predicted,'after_predicted':LABELS[int(probs.argmax())],
                               'before_value':float(matrices[s][i,40]),'after_value':train_path_median,
                               **{'before_p_'+l:float(predictions[s][i,j]) for j,l in enumerate(LABELS)},
                               **{'after_p_'+l:float(probs[j]) for j,l in enumerate(LABELS)}})
    aggregates=[]
    for (s,dimension,actual,value),entries in sorted(buckets.items(),key=lambda item:str(item[0])):
        counts=Counter(e['predicted'] for e in entries)
        aggregates.append({'split':s,'dimension':dimension,'actual':actual,'value':value,'rows':len(entries),
                           **{'predicted_'+l:counts[l] for l in LABELS}})
    signal_table=[]
    for s in sets:
        for marker in (False,True):
            selected=[d for d in details if d['split']==s and d['actual']=='sqli' and d['payload_sql_comment_signal']==marker]
            counts=Counter(d['predicted'] for d in selected)
            signal_table.append({'split':s,'comment_signal':marker,'rows':len(selected),**{l:counts[l] for l in LABELS}})
    probe_summary=[]
    for s,probe,actual in sorted({(p['split'],p['probe'],p['actual']) for p in probes}):
        selected=[p for p in probes if (p['split'],p['probe'],p['actual'])==(s,probe,actual)]
        probe_summary.append({'split':s,'probe':probe,'actual':actual,'rows':len(selected),
                              'prediction_changes':sum(p['before_predicted']!=p['after_predicted'] for p in selected),
                              'before':dict(Counter(p['before_predicted'] for p in selected)),
                              'after':dict(Counter(p['after_predicted'] for p in selected))})
    # TreeSHAP decomposes raw score differences, not causal effects or calibrated probabilities.
    shap_details=[];shap_groups=defaultdict(list)
    for s,rows in sets.items():
        if s=='train':continue
        selected=[i for i,r in enumerate(rows) if focus(label(r),LABELS[int(predictions[s][i].argmax())])]
        if not selected:continue
        contributions=model.get_booster().predict(DMatrix(matrices[s][selected]),pred_contribs=True)
        margins=model.get_booster().predict(DMatrix(matrices[s][selected]),output_margin=True)
        if not np.allclose(contributions.sum(axis=2),margins,atol=2e-5):raise ValueError('TreeSHAP分解不守恆')
        for j,i in enumerate(selected):
            row=rows[i];actual=label(row);predicted=LABELS[int(predictions[s][i].argmax())]
            delta=contributions[j,LABELS.index(predicted),:-1]-contributions[j,LABELS.index(actual),:-1]
            grouped=Counter()
            for k,value in enumerate(delta):
                name=feature_names[k]
                group=name.split('.hash_bucket.')[0]+'.hash_buckets' if '.hash_bucket.' in name else name
                grouped[group]+=float(value)
            shap_groups[s,focus(actual,predicted)].append(grouped)
            for k in np.argsort(-delta)[:8]:
                shap_details.append({'split':s,'sample_id':row['sample_id'],'actual':actual,'predicted':predicted,
                                     'feature':feature_names[k],'value':float(matrices[s][i,k]),
                                     'shap_predicted_minus_actual_margin':float(delta[k])})
    shap_summary=[]
    for (s,category),items in sorted(shap_groups.items()):
        keys=set().union(*(set(v) for v in items))
        averages={k:sum(v[k] for v in items)/len(items) for k in keys}
        shap_summary.append({'split':s,'focus':category,'rows':len(items),
                             'top_group_margin_contributions':sorted(averages.items(),key=lambda kv:(-kv[1],kv[0]))[:8]})
    gains=model.get_booster().get_score(importance_type='total_gain')
    importances=[{'feature':feature_names[int(k[1:])],'total_gain':float(v)} for k,v in sorted(gains.items(),key=lambda kv:-kv[1])]
    summary={'scope':'offline diagnostic only; fixed train-only model, no hyperparameter search or dataset changes',
             'feature_version':VERSION,'feature_count':2402,'packages':{n:importlib.metadata.version(n) for n in ('numpy','scikit-learn','xgboost')},
             'data_sha256':before,'prediction_sha256':prediction_sha,'document_sha256':doc_hashes,
             'max_prediction_reproduction_error':max_error,'evaluation_rows':sum(len(sets[s]) for s in sets if s!='train'),
             'error_rows':sum(d['actual']!=d['predicted'] for d in details if d['split']!='train'),
             'focus_rows':dict(Counter(d['focus'] for d in details if d['focus'])),
             'sql_comment_table':signal_table,'counterfactual_summary':probe_summary,
             'attack_vectors_equal_to_normal_control':sum(d['changed_features_vs_normal_pair']==0 for d in details if d['actual']!='normal'),
             'tree_shap_summary':shap_summary,'train_normal_path_length_median':train_path_median,
             'source_sha256':{n:sha(Path(__file__).with_name(n)) for n in ('diagnose_v4_errors.py','features.py','request_input.py')},
             'no_original_inputs_changed':before=={s:sha(p) for s,p in paths.items()}}
    if not summary['no_original_inputs_changed']:raise RuntimeError('原始資料意外更動')
    output.mkdir(parents=True)
    write_csv(output/'samples.csv',details)
    write_csv(output/'focus-errors.csv',[d for d in details if d['focus']])
    write_csv(output/'all-evaluation-errors.csv',[d for d in details if d['split']!='train' and d['actual']!=d['predicted']])
    write_csv(output/'group-breakdown.csv',aggregates)
    write_csv(output/'counterfactuals.csv',probes)
    write_csv(output/'feature-gain.csv',importances)
    write_csv(output/'error-shap.csv',shap_details)
    (output/'audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# v4逐筆誤判與特徵敏感度診斷','',
           '固定150棵／深度3／學習率0.05，僅fit train；先逐筆核對既有預測（機率誤差≤1e-6）才分析。沒有重新切分、調參、送HTTP或改寫原始資料。',
           '',f'評估共{summary["evaluation_rows"]}筆，誤判{summary["error_rows"]}筆；本次三類重點：'+json.dumps(summary['focus_rows'],ensure_ascii=False)+'。',
           '', '## SQLi註解特徵的資料偏差','',
           '| 集合 | 命中註解特徵 | 筆數 | 判normal | 判sqli | 判xss |','|---|---|---:|---:|---:|---:|']
    for r in signal_table:lines.append(f'| {r["split"]} | {r["comment_signal"]} | {r["rows"]} | {r["normal"]} | {r["sqli"]} | {r["xss"]} |')
    lines += ['', '註解特徵是現行正則 `--|/\*|\*/`，不包含MySQL的`#`。命中只是字串訊號，不是SQL執行證據。訓練SQLi全部含此訊號，缺少不帶註解的結構，也缺少帶相同符號的正常自由文字對照。',
              '', '## 僅在副本上的敏感度測試','',
              '| 集合 | 操作 | 筆數 | 改變預測 | 原本分布 | 修改後分布 |','|---|---|---:|---:|---|---|']
    for r in probe_summary:lines.append(f'| {r["split"]} | {r["probe"]} | {r["rows"]} | {r["prediction_changes"]} | {r["before"]} | {r["after"]} |')
    lines += ['', '以上是特徵敏感度探針，替換後的值不是新增訓練資料或實機有效SQL；文字長度控制為Python字元數，沒有控制UTF-8位元組長度、語意或每個ngram，不能據此斷言中文本身造成誤報。未對照部署效果或校準門檻。',
              '', '## API文件與標籤限制','',
              'samples.csv及focus-errors.csv逐筆連結文件欄位、行號、含義、型別與可輸入值；不改三份API文件。攻擊只表示payload來源意圖，在語言／貨幣／數字欄可能不合型別或enum。正常候選也未實機驗證，不能把它們的誤報率當作真實商店使用者誤報率。',
              '', 'SQL結構片段CASE／COLLATE只有在可執行SQL語境才有注入意義；作搜尋文字也可為字面內容。僅憑請求無法證明惡意成功，保留原標籤與脈絡限制，不為提高分數重新標記。',
              '', '## 特徵能否看到差異','',
              f'攻擊與其正常配對2402維完全相同的樣本：{summary["attack_vectors_equal_to_normal_control"]}筆。可見差異不代表樹有學到有效決策。feature-gain.csv是模型分裂增益，不是因果解釋；hash桶有碰撞，不把桶名解釋成唯一關鍵字。',
              '', '## 後續補強的界線','',
              '目前test／validation／challenge已被檢視，只作診斷，不反覆改到高分。保留這些資料與參數；若新增train，先與完整骨架目錄比對，碰到任何保留骨架就排除，不能把本輪錯題複製到train。',
              '', '優先新增獨立來源的不帶註解SQL結構、不同SQL方言與字面程式碼／符號正常對照。依既有API文件只將正常文字放合適自由文字欄，保持三類相同位置分布與近似長度；分開記錄不合型別的攻擊候選。需另建立新且未檢視的跨來源評估集，不能沿用本輪資料宣稱最終泛化。',
              '', '本輪診斷不新增訓練資料、不改模型或打包檔，避免把診斷當成模型改進已驗證。完整逐筆證據見同目錄CSV與audit.json。']
    lines += ['', '## TreeSHAP分數分解與路徑長度探針','',
              'error-shap.csv保存重點誤判的前8項貢獻。分解的是預測類別減真實類別的原始margin差，非機率或因果效果；已核對加總守恆。hash桶可能碰撞。',
              '', '| 集合 | 誤判類型 | 筆數 | 平均正向貢獻最高群 |','|---|---|---:|---|']
    for r in shap_summary:
        rendered='；'.join(k+': '+format(v,'.3f') for k,v in r['top_group_margin_contributions'][:4])
        lines.append(f'| {r["split"]} | {r["focus"]} | {r["rows"]} | {rendered} |')
    lines += ['', 'path_length_feature_only只把特徵向量第40格設為train正常樣本中位數，原始path與所有其他特徵不動。這是數值敏感度探針，向量可能不對應任何真實HTTP請求，不能當作資料正規化、修正後模型或新評估成績。']
    (output/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return {k:summary[k] for k in ('evaluation_rows','error_rows','focus_rows','max_prediction_reproduction_error','no_original_inputs_changed')}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',type=Path,default=ROOT/'sentinel/dataset/small-api-v4')
    p.add_argument('--results-dir',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(diagnose(a.data_dir,a.results_dir or a.data_dir/'evaluation-smoke',a.output),ensure_ascii=False))
