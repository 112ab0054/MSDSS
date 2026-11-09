"""只擴充train的正常傳輸header情境；三類同profile，保留題原檔凍結。"""
import argparse
from collections import Counter,defaultdict
import copy
import csv
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'sentinel/model'))
from data_io import read_rows
from build_small_dataset import sha,write_csv,read_documents,field_value
from build_train_v5 import flat

PROFILES=[
 {'name':'json_client','headers':{'Accept':'application/json','Accept-Encoding':'gzip, deflate','Connection':'keep-alive','User-Agent':'msdss-client/1.0','Host':'localhost'}},
 {'name':'httpx_any','headers':{'Accept':'*/*','Accept-Encoding':'gzip, deflate','Connection':'keep-alive','User-Agent':'python-httpx/0.28.1','Host':'localhost'}},
 {'name':'application_range','headers':{'Accept':'application/*;q=0.9,application/json','Accept-Encoding':'gzip, deflate, br','Connection':'keep-alive','User-Agent':'Mozilla/5.0','Host':'localhost'}},
 {'name':'browser_ranges','headers':{'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8','Accept-Encoding':'gzip, deflate, br','Connection':'keep-alive','User-Agent':'Mozilla/5.0','Host':'localhost'}}]


def apply_profile(request,profile):
    request=copy.deepcopy(request)
    overwritten={k.lower() for k in profile['headers']}
    request['headers']={k:v for k,v in request['headers'].items() if k.lower() not in overwritten}
    request['headers'].update(profile['headers'])
    return request


def build(source,output):
    if output.exists():raise ValueError('輸出已存在，請指定新目錄')
    sets={s:read_rows(source/(s+'.csv')) for s in ('train','test','validation','challenge')}
    hashes={s:sha((source/(s+'.csv')).read_bytes()) for s in sets}
    triples=defaultdict(list)
    for row in sets['train']:triples[row['metadata']['pair_group']].append(row)
    triples=[rs for _,rs in sorted(triples.items()) if len(rs)==3]
    used={sha(r['input']) for rows in sets.values() for r in rows};selection_use=Counter();op_use=Counter();extra=[];bindings=[]
    for profile in PROFILES:
        selected=0
        for group in sorted(triples,key=lambda rs:(selection_use[rs[0]['metadata']['pair_group']],op_use[rs[0]['metadata']['platform'],rs[0]['metadata']['operation_path']],rs[0]['metadata']['pair_group'])):
            requests=[apply_profile(r['input'],profile) for r in group]
            if any(sha(req) in used for req in requests):continue
            normal_index=next(i for i,r in enumerate(group) if r['annotation']['proposed_label']=='normal')
            pair=sha(['v6-transport',profile['name'],group[0]['metadata']['pair_group']]);normal_id=sha([pair,'normal',requests[normal_index]])
            for row,req in zip(group,requests):
                r=copy.deepcopy(row);label=r['annotation']['proposed_label']
                r['sample_id']=sha([pair,label,req]);r['input']=req
                r['metadata'].update(pair_group=pair,origin='document-v6-transport-offline',transport_profile=profile['name'],
                                     original_train_sample_id=row['sample_id'],augmentation_revision='transport-v6')
                if label!='normal':r['metadata']['control_sample_id']=normal_id
                extra.append(r);used.add(sha(req))
                bindings.append({'sample_id':r['sample_id'],'original_train_sample_id':row['sample_id'],'class':label,
                                 'platform':r['metadata']['platform'],'api':r['metadata']['operation_path'],
                                 'transport_profile':profile['name'],'transport_headers':json.dumps(profile['headers'],ensure_ascii=False),
                                 'raw_path_query_body_unchanged':True,'http_executed':False})
            selected+=1;selection_use[group[0]['metadata']['pair_group']]+=1
            op_use[group[0]['metadata']['platform'],group[0]['metadata']['operation_path']]+=1
            if selected==9:break
        if selected!=9:raise ValueError('可用配對不足：'+profile['name'])
    sets['train']+=extra;output.mkdir(parents=True)
    for name in ('test.csv','validation.csv','challenge.csv','skeleton-catalog.csv','external-payloads.csv','HTTPPARAMS-LICENSE.txt','augmentation-bindings.csv','candidate-decisions.csv'):
        shutil.copy2(source/name,output/name)
    write_csv(output/'train.csv',[flat(r) for r in sets['train']]);write_csv(output/'transport-augmentation.csv',bindings)
    with (source/'field-coverage.csv').open(encoding='utf-8-sig',newline='') as f:coverage=list(csv.DictReader(f))
    for c in coverage:
        rows=[r for values in sets.values() for r in values if (r['metadata']['platform'],r['input']['method'],r['metadata']['operation_path'])==(c['平台'],c['方法'],c['API'])]
        c['存在筆數']=sum(c['參數']=='（本文）' or field_value(r['input'],c['位置'],c['參數'])[0] for r in rows)
        if not c['存在筆數']:raise ValueError('文件欄位遺漏')
    write_csv(output/'field-coverage.csv',coverage)
    saved=json.loads((source/'provenance.json').read_text(encoding='utf-8'))
    saved.update(dataset_revision='v6-transport-augmentation',main_ratio='702:150:150; holdouts frozen',
        baseline_csv_sha256=hashes,required_feature_version=6,
        frozen_holdout_sha256={s:hashes[s] for s in ('test','validation','challenge')},
        splits={s:{'rows':len(rs),'labels':dict(Counter(r['annotation']['proposed_label'] for r in rs)),'platforms':dict(Counter(r['metadata']['platform'] for r in rs))} for s,rs in sets.items()},
        transport_augmentation={'triples':36,'rows':108,'per_class':36,'profiles':PROFILES,'business_fields_changed':False,'all_from_train':True},
        source_generators_sha256={n:sha(Path(__file__).with_name(n).read_bytes()) for n in ('build_transport_v6.py','build_train_v5.py')})
    (output/'provenance.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'README.md').write_text("""# v6：正常HTTP header情境與Accept語意修正

train702（每類234），test150、Sylius validation150、challenge96原CSV凍結，共1098筆。原594筆train保留，僅新增36組三類配對108筆；相同profile同時給normal／SQLi／XSS，不把客戶端與類別綁定。
新增Accept、Accept-Encoding、Connection、User-Agent、Host是HTTP傳輸header，保留所有原有API文件欄位及非覆寫業務headers；不捏造新API參數。路徑、query、本文與攻擊原文不變，沒有使用Medusa樣本訓練。
特徵v6仍2402維，只修正合法Accept媒體型別萬用字元不算SQL註解；其餘header內容與所有raw ngram仍分析。不刪header、不正規化原文、不調分類門檻。舊v5模型不能混用新特徵。
所有資料仍offline候選、HTTP=0。保留題已被檢視，只供探索性比較；真實Medusa購物業務流程尚未完成驗收。正常長路徑缺口、條件商品與歷史ID限制仍保留。
"""+'\n```json\n'+json.dumps(saved,ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
    return saved['splits']


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'sentinel/dataset/small-api-v5')
    p.add_argument('--output',type=Path,default=ROOT/'sentinel/dataset/small-api-v6')
    a=p.parse_args();print(json.dumps(build(a.source,a.output),ensure_ascii=False))
