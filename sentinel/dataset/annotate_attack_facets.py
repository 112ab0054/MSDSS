"""新增一個CSV顯示欄位；不改完整紀錄JSON、原始請求、三類標籤或分組。"""
import argparse
from collections import Counter
import csv
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[2]
VERSION=1
COLUMN='攻擊面向'
SPLITS=('train','test','validation','challenge')


def matches(pattern,value):return bool(re.search(pattern,value,re.I))


def attack_facets(row):
    label=row['annotation'].get('label',row['annotation'].get('proposed_label'))
    if label=='normal':return ['不適用']
    payload=row['metadata'].get('payload') or {}
    raw=payload.get('value')
    if not isinstance(raw,str):return ['缺少payload，無法判讀']
    # 僅輔助判讀一次URL／HTML解碼，與前次唯讀統計的定義一致；絕不寫回request。
    view=html.unescape(unquote(raw));family=payload.get('family');tags=[]
    def add(name,condition):
        if condition:tags.append(name)
    if label=='sqli':
        add('布林／條件字樣',matches(r'\b(and|or|xor|between|like|exists)\b|\bin\s*\(|\bif\s*\(',view) or family=='sql.boolean')
        add('UNION聯集',matches(r'\bunion\b',view))
        add('時間／高耗時相關',family=='sql.time' or matches(r'sleep\s*\(|benchmark\s*\(|receive_message\s*\(|generate_series\s*\(|repeat\s*\([^;]+500000000|select count\(\*\) from [^;]+ as t1,[^;]+ as t2',view))
        add('錯誤觸發相關',family=='sql.error' or matches(r'extractvalue\s*\(|updatexml\s*\(|\bas numeric\b|exp\s*\(\s*~|1/\(select 0\)',view))
        add('分號接續多語句',matches(r';\s*(select|begin|call)\b',view))
        add('排序／條件等SQL結構片段',matches(r'\border\s+by\b|\bcollate\b|\bcase\s+when\b|\bcase\s+\d',view) or family=='sql.structure')
        add('SELECT／子查詢',matches(r'\bselect\b',view))
        add('函式／型別轉換',matches(r'\b(?:length|json_extract|sleep|benchmark|concat|coalesce|nullif|ascii|substring|current_database|cast|convert|regexp_like|position|hex|mod|round|chr|char|elt|exp|extractvalue|count)\s*\(',view))
    elif label=='xss':
        add('script標籤',matches(r'<script\b',view))
        add('事件屬性',matches(r'\bon\w+\s*=',view))
        add('javascript網址',matches(r'javascript\s*:',view))
        add('JS字串／引號邊界',family=='xss.js-string' or (payload.get('source')=='local_curated_train_v5' and view.startswith(('"',"'"))))
        add('JS模板插值','${' in view)
        add('JS註解邊界專用片段',family=='xss.js-comment-boundary')
        add('CSS／style／filter',matches(r'<style\b|\bstyle\s*=|\bfilter\s*:',view))
        add('data／mhtml／mocha協定',matches(r'\b(?:data|mhtml|mocha):',view))
        add('CDATA／HTML註解混淆',matches(r'cdata|<!--',view))
        add('舊式&{...}表達式','&{' in view)
    else:raise ValueError('不支援的標籤：'+str(label))
    add('原文編碼變體',matches(r'%[0-9a-f]{2}|\\u[0-9a-f]{4}|&#(?:x[0-9a-f]+|[0-9]+);|&(?:lt|gt|quot|apos);',raw))
    if not tags:
        if label=='xss' and matches(r'<img\b[^>]*\bsrc\s*=',view):tags=['外部資源載入（XSS標註待確認）']
        else:tags=['其他片段（未細分）']
    return tags


def sha(raw):return hashlib.sha256(raw).hexdigest()


def annotate(source,output):
    if output.exists():raise ValueError('輸出已存在，請指定新目錄；原v6保留不覆寫')
    counts={};source_sha={};annotated_sha={};record_sha={};all_rows=0
    output.mkdir(parents=True)
    for split in SPLITS:
        path=source/(split+'.csv');source_sha[split]=sha(path.read_bytes())
        with path.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
        if COLUMN in fields:raise ValueError('來源已有攻擊面向欄，避免重複標註')
        summaries=Counter()
        for row in rows:
            tags=attack_facets(json.loads(row['完整紀錄JSON']));row[COLUMN]='；'.join(tags);summaries.update(tags)
        # 新欄放在類別旁；所有原欄與完整紀錄JSON的字串原值保持不變。
        new_fields=list(fields);new_fields.insert(new_fields.index('類別')+1,COLUMN)
        with (output/path.name).open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=new_fields);writer.writeheader();writer.writerows(rows)
        with (output/path.name).open(encoding='utf-8-sig',newline='') as f:readback=list(csv.DictReader(f))
        assert [{k:r[k] for k in fields} for r in readback]==[{k:r[k] for k in fields} for r in rows]
        record_sha[split]=sha(json.dumps([r['完整紀錄JSON'] for r in rows],ensure_ascii=False,separators=(',',':')).encode())
        annotated_sha[split]=sha((output/path.name).read_bytes());counts[split]=dict(summaries);all_rows+=len(rows)
    for name in ('skeleton-catalog.csv','field-coverage.csv','external-payloads.csv','HTTPPARAMS-LICENSE.txt',
                 'augmentation-bindings.csv','candidate-decisions.csv','transport-augmentation.csv','parser-compatibility.json'):
        if (source/name).is_file():shutil.copy2(source/name,output/name)
    saved=json.loads((source/'provenance.json').read_text(encoding='utf-8'))
    saved['display_annotation']={'version':VERSION,'column':COLUMN,'separator':'；','source_dataset':'sentinel/dataset/small-api-v6',
        'unannotated_csv_sha256':source_sha,'annotated_csv_sha256':annotated_sha,
        'complete_record_json_values_sha256':record_sha,'rule_source_sha256':sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')),
        'rule_source_hash_format':'LF text bytes; request bytes unchanged','original_columns_and_json_unchanged':True,'used_as_model_feature':False,
        'meaning':'multi-label visible syntax/family annotation; not verified exploit effect'}
    saved['unannotated_holdout_sha256']={s:source_sha[s] for s in ('test','validation','challenge')}
    saved['frozen_holdout_sha256']={s:annotated_sha[s] for s in ('test','validation','challenge')}
    (output/'provenance.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
    rules={'version':VERSION,'column':COLUMN,'rows':all_rows,'counts_by_split':counts,
           'rules_source':'sentinel/dataset/annotate_attack_facets.py','rule_source_sha256':sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')),
           'rule_source_hash_format':'LF text bytes; request bytes unchanged','multi_label':True,'normal_value':'不適用','model_input':False,
           'notes':['依既有family與原文可見語法判斷，部分時間／錯誤標籤為推定相關寫法，未驗證執行效果',
                    '輔助判讀只解一次URL與HTML實體，不改原文或模型輸入',
                    '不推定反射型／儲存型／DOM型或第二階段注入，需要實際流程證據',
                    '同筆可多標籤，面向筆數不能相加作請求總數',
                    '不因本欄改動normal／sqli／xss標籤；原有111筆normal語言ID格式及外部XSS標註疑義仍未修正']}
    (output/'attack-facets-rules.json').write_text(json.dumps(rules,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'README.md').write_text("""# v6攻擊面向閱讀版

本版只在四份CSV的「類別」旁新增一欄「攻擊面向」，多面向用全形分號分隔。normal顯示不適用；可見結構不足者標成待確認或未細分。不是已驗證的攻擊效果，也不假造反射型／儲存型／DOM型標註。
原small-api-v6完整保留，1098筆、sample ID、三類標籤、原始請求、完整紀錄JSON與骨架／集合不變。因為加了顯示欄，CSV整檔SHA必然改變；本目錄的凍結SHA明確對應閱讀版，原始SHA另外保存，不能把新SHA假稱為舊CSV完全一樣。
訓練讀取完整紀錄JSON，不讀這個顯示欄，模型／推論特徵與結果不因此改變，不需重新訓練。新Colab套件會帶這些CSV。
規則、計數與限制見attack-facets-rules.json；原始欄位與完整紀錄逐筆讀回核對一致，來源追溯見provenance.json的display_annotation。
本輪不處理前次分析指出的111筆normal的sw-language-id格式問題，也不更改外部來源XSS標籤；這些問題仍保留待後續處理。
""",encoding='utf-8')
    return {'rows':all_rows,'column':COLUMN,'counts_by_split':counts}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'sentinel/dataset/small-api-v6')
    p.add_argument('--output',type=Path,default=ROOT/'sentinel/dataset/small-api-v6-annotated')
    a=p.parse_args();print(json.dumps(annotate(a.source,a.output),ensure_ascii=False))
