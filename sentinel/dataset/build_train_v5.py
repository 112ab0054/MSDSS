"""僅擴充v4的train；凍結三份保留CSV、骨架規則與模型參數。"""
import argparse
from collections import Counter,defaultdict
import copy
import csv
from difflib import SequenceMatcher
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'sentinel/model'))
from data_io import read_rows
from skeletons import group_catalog,analysis_view,parser_fingerprints,PROTOCOL
from build_small_dataset import read_documents,field_value,finalize,sha,write_csv
from build_xss_v3 import targets,set_field

SQL=[
 "' AND EXISTS(SELECT 1 FROM information_schema.tables)",
 "' AND NOT EXISTS(SELECT 1 FROM information_schema.columns)",
 "0 UNION DISTINCT SELECT CONCAT('catalog','item')",
 "(SELECT COALESCE(NULLIF('catalog',''), 'fallback'))",
 "1 BETWEEN 0 AND 2", "1 IN (SELECT 1)", "1 OR EXISTS(SELECT 1)",
 "1 AND ASCII(SUBSTRING(CURRENT_USER,1,1))>64",
 "1 AND 0=(SELECT COUNT(*) FROM information_schema.tables)",
 "'||(SELECT CURRENT_DATABASE())||'", "1 XOR 0", "IF(1=1,1,0)",
 "COALESCE((SELECT NULL),1)", "1 AND REGEXP_LIKE('catalog','^cat')",
 "1 AND CAST('7' AS INTEGER)=7", "1 AND CONVERT(7,CHAR)='7'",
 "1 AND LENGTH(CURRENT_DATABASE())>0", "1 AND CURRENT_USER IS NOT NULL",
 "1 AND 'catalog' SIMILAR TO 'cat%'", "1 AND POSITION('a' IN 'catalog')>0",
 "1 AND HEX('catalog') LIKE '63%'", "1 AND MOD(9,2)=1", "1 AND ROUND(1.2)=1",
 "1 AND 1=ANY(SELECT 1)"]
XSS=[
 '";alert()//', "'+confirm()+'", "'-alert()-'", '";prompt();var q="',
 'oncut=alert()', 'oncopy=confirm()', 'onpaste=prompt()',
 'javascript:alert?.()', '${alert?.()}', '${confirm?.()}',
 '<svg/onload=alert?.()>', '<img src=x onerror=confirm?.()>',
 '";window["alert"]()//', "';globalThis.confirm()//", '`${prompt?.()}`',
 '<input autofocus onfocus=prompt?.()>', '<details open ontoggle=alert?.()>',
 '<a href=javascript:confirm?.()>open</a>', '<iframe src=javascript:prompt?.()>',
 '";(()=>alert())()//', '";[1].map(()=>confirm())//',
 '${(()=>prompt())()}', '";Reflect.apply(alert,null,[])//',
 '<svg onload="setTimeout(()=>alert(),0)"></svg>']
BENIGN=[
 'Book title: SQL comments -- a guide', 'Literal /* comment */ in a tutorial',
 'Customer note -- leave at reception', 'Template symbols -- ${item.name}',
 'HTML reference -- <b>cotton</b>', 'Encoding guide -- %3C is literal text',
 'JavaScript book -- onload= examples', 'Colour choice -- navy and white',
 'Study notes -- console.log syntax', "Quote guide -- O'Connor examples",
 'Text /* example */ from a manual', 'Shipment note -- use the side door',
 'Search phrase -- HTML attributes', 'Catalog note -- size and material',
 'Learning notes -- query parameters', 'Comment markers -- printed on paper',
 'TypeScript book -- optional calls', 'Fabric guide -- care instructions',
 'Template guide -- curly brackets', 'Notebook -- literal # and $ symbols',
 'A label /* draft */ for a sample', 'Reference -- javascript: URL syntax',
 'Product note -- collect in store', 'Textbook -- SQL and HTML chapters']
COMPANIES=['North -- South Trading','Cotton -- Linen Studio','Paper -- Ink Books',
 'Blue -- White Goods','Garden -- Home Supply','Maple -- Cedar Works',
 'East -- West Textiles','Town -- Country Shop']


def free_fields(req,op):
    fields=[]
    for (loc,name),spec in op['fields'].items():
        if loc not in ('body','query') or 'string' not in spec['type'] or '固定值：' in spec['values']:continue
        if name.split('.')[-1] not in ('search','query','term','notes','specialNote','label','description','companyName'):continue
        if field_value(req,loc,name)[0]:fields.append((loc,name))
    return fields


def filter_candidates(catalogue):
    existing=[dict(e,label=e['class']) for e in catalogue]
    accepted=[];decisions=[]
    for label,values in [('sqli',SQL),('xss',XSS)]:
        for i,value in enumerate(values):
            candidate={'label':label,'value':value,'family':f'{label}.train-v5-curated',
                       'template':f'curated-v5:{label}:{i}','source':'local_curated_train_v5'}
            g,s=group_catalog(existing+accepted+[candidate]);last=len(g)-1
            old_match=any(g[j]==g[last] for j in range(len(existing)))
            near=any(e['label']==label and SequenceMatcher(None,analysis_view(value),analysis_view(e['value']),autojunk=False).ratio()>=.90 for e in existing)
            reason='existing_skeleton_overlap' if old_match else 'existing_raw_near_overlap' if near else 'new_training_skeleton'
            decisions.append({'class':label,'value':value,'template':candidate['template'],'decision':reason})
            if not (old_match or near):accepted.append(candidate)
    if any(sum(e['label']==l for e in accepted)<8 for l in ('sqli','xss')):raise ValueError('獨立新骨架候選不足')
    g,s=group_catalog(existing+accepted)
    if any(g[i]!=r['skeleton_group_id'] or s[i]!=r['skeleton_signature'] for i,r in enumerate(catalogue)):
        raise ValueError('新增案例改變既有骨架，不能修改保留題的分組')
    pool=defaultdict(list);new_catalog=[]
    for j,e in enumerate(accepted,len(existing)):
        payload={k:v for k,v in e.items() if k!='label'}
        payload.update(skeleton_group_id=g[j],skeleton_signature=s[j],skeleton_rule_version=1)
        pool[e['label']].append(payload)
        new_catalog.append({'class':e['label'],'value':e['value'],'family':e['family'],'template':e['template'],'source':e['source'],
                            'origin_split':'train','assigned_split':'train','excluded_local_overlap':False,
                            'assignment_reason':'new_train_only_curated_not_selected_by_metrics',
                            'skeleton_group_id':g[j],'skeleton_signature':s[j],'skeleton_rule_version':1})
    return pool,new_catalog,decisions


def flat(row):
    r=row;m=r['metadata'];req=r['input']
    return {'樣本ID':r['sample_id'],'平台':m['platform'],'集合':m['split'],'類別':r['annotation']['proposed_label'],
            '方法':req['method'],'API':m['operation_path'],'Header_JSON':json.dumps(req['headers'],ensure_ascii=False),
            'Query_JSON':json.dumps(req['query'],ensure_ascii=False),'Body_JSON':json.dumps(req['body'],ensure_ascii=False),
            'Path':req['path'],'原始Query':req['raw_query'],'原始Body':req['raw_body'],
            'Payload原文':(m.get('payload') or {}).get('value'),'完整紀錄JSON':json.dumps(r,ensure_ascii=False)}


def build(source,output):
    if output.exists():raise ValueError('輸出已存在，不能覆寫基準')
    with (source/'skeleton-catalog.csv').open(encoding='utf-8-sig',newline='') as f:catalogue=list(csv.DictReader(f))
    pool,new_catalog,decisions=filter_candidates(catalogue)
    sets={s:read_rows(source/(s+'.csv')) for s in ('train','test','validation','challenge')}
    ops,doc_hashes=read_documents();original_hashes={s:sha((source/(s+'.csv')).read_bytes()) for s in sets}
    used={sha(r['input']) for rows in sets.values() for r in rows};extra=[];bindings=[];counts=Counter();payload_use=Counter()
    normals=[r for r in sets['train'] if r['annotation']['proposed_label']=='normal']
    for loc in ('header','body','query','path'):
        bases=[]
        for r in normals:
            m=r['metadata'];key=m['platform'],r['input']['method'],m['operation_path'];op=ops[key]
            free=free_fields(r['input'],op)
            if loc in targets(r['input'],op) and free:bases.append((r,key,free))
        if not bases:raise ValueError('沒有文件允許的正常文字欄位與攻擊位置：'+loc)
        for index in range(12):
            selected=None
            for base,key,free in sorted(bases,key=lambda t:(counts[t[1][0]],counts[t[1]],t[0]['sample_id'])):
                for field in free:
                    text=(COMPANIES[index%len(COMPANIES)] if field[1].split('.')[-1]=='companyName' else BENIGN[(index+12*('header','body','query','path').index(loc))%len(BENIGN)])
                    req=copy.deepcopy(base['input']);set_field(req,*field,text);finalize(req,key[2])
                    if sha(req) not in used:selected=base,key,field,text,req;break
                if selected:break
            if not selected:raise ValueError('文件正常控制無法保持唯一，不以亂改ID湊數')
            base,key,free,text,req=selected;counts[key]+=1;counts[key[0]]+=1
            used.add(sha(req));pair=sha(['train-augmentation-v5',req]);normal_id=sha([pair,'normal',req])
            common={**copy.deepcopy(base['metadata']),'pair_group':pair,'origin':'document-v5-train-only-offline',
                    'benign_content_context':{'value':text,'source':'document_normal_contrast_v5'},
                    'augmentation_revision':'train-v5','schema_validity':'not_validated','business_verified':False}
            normal={'sample_id':normal_id,'input':req,'annotation':{'proposed_label':'normal','label_basis':'document free text/company test data; business success unverified'},
                    'metadata':{**common,'payload':None,'target_location':None,'target_parameter':None,'template_id':None}}
            extra.append(normal)
            available=targets(req,ops[key])[loc]
            parameter=min(available,key=lambda n:(counts[key,loc,n],n));counts[key,loc,parameter]+=1
            target_spec=ops[key]['fields'][loc,parameter];normal_spec=ops[key]['fields'][free]
            for label in ('sqli','xss'):
                candidates=sorted(pool[label],key=lambda p:(payload_use[label,p['template']],p['template']))
                chosen=None
                for payload in candidates:
                    attack=copy.deepcopy(req);set_field(attack,loc,parameter,payload['value']);finalize(attack,key[2])
                    if sha(attack) not in used:chosen=payload;break
                if chosen is None:raise ValueError('新攻擊原文不足')
                payload_use[label,chosen['template']]+=1;used.add(sha(attack))
                meta={**common,'payload':chosen,'target_location':loc,'target_parameter':parameter,
                      'template_id':sha([label,chosen['template']]),'control_sample_id':normal_id,'value_may_violate_document_constraints':True,
                      **{k:chosen[k] for k in ('skeleton_group_id','skeleton_signature','skeleton_rule_version')}}
                extra.append({'sample_id':sha([pair,label,attack]),'input':attack,
                              'annotation':{'proposed_label':label,'label_basis':'curated fragment intent; requires matching SQL/JS context; no exploit success claim'},'metadata':meta})
                bindings.append({'sample_id':extra[-1]['sample_id'],'platform':key[0],'method':key[1],'api':key[2],
                                 'class':label,'location':loc,'parameter':parameter,'document_type':target_spec['type'],
                                 'document_meaning':target_spec['meaning'],'document':target_spec['source'],'document_line':target_spec['line'],
                                 'normal_text_location':free[0],'normal_text_parameter':free[1],'normal_text_meaning':normal_spec['meaning'],
                                 'normal_literal':text,'payload':chosen['value'],'http_executed':False})
    sets['train']+=extra
    output.mkdir(parents=True)
    for s in ('test','validation','challenge'):shutil.copy2(source/(s+'.csv'),output/(s+'.csv'))
    write_csv(output/'train.csv',[flat(r) for r in sets['train']])
    write_csv(output/'skeleton-catalog.csv',catalogue+new_catalog)
    write_csv(output/'candidate-decisions.csv',decisions);write_csv(output/'augmentation-bindings.csv',bindings)
    for name in ('external-payloads.csv','HTTPPARAMS-LICENSE.txt'):shutil.copy2(source/name,output/name)
    with (source/'field-coverage.csv').open(encoding='utf-8-sig',newline='') as f:coverage=list(csv.DictReader(f))
    for row in coverage:
        matches=[r for rows in sets.values() for r in rows if (r['metadata']['platform'],r['input']['method'],r['metadata']['operation_path'])==(row['平台'],row['方法'],row['API'])]
        row['存在筆數']=sum(row['參數']=='（本文）' or field_value(r['input'],row['位置'],row['參數'])[0] for r in matches)
        if not row['存在筆數']:raise ValueError('遺漏文件欄位')
    write_csv(output/'field-coverage.csv',coverage)
    saved=json.loads((source/'provenance.json').read_text(encoding='utf-8'))
    summary={**saved,'dataset_revision':'v5-train-augmentation','main_ratio':'594:150:150; holdouts frozen, not 60:20:20',
             'skeleton_catalog_sha256':sha((output/'skeleton-catalog.csv').read_bytes()),
             'skeleton_parser':parser_fingerprints(),'parameter_document_sha256':doc_hashes,
             'frozen_holdout_sha256':{s:original_hashes[s] for s in ('test','validation','challenge')},
             'baseline_csv_sha256':original_hashes,'augmentation':{'triples':48,'rows':144,'per_class':48,
                  'platforms':dict(Counter(r['metadata']['platform'] for r in extra)),
                  'new_payloads_per_class':{l:len(pool[l]) for l in pool},'decisions':dict(Counter(r['decision'] for r in decisions)),
                  'source':'locally curated SQL/JS fragments and documented normal contrast; not new external corpus',
                  'evaluation_already_inspected':True,'normal_long_path_gap':'no fabricated routes/IDs; still unresolved'},
             'splits':{s:{'rows':len(rows),'labels':dict(Counter(r['annotation']['proposed_label'] for r in rows)),
                          'platforms':dict(Counter(r['metadata']['platform'] for r in rows))} for s,rows in sets.items()},
             'source_generators_sha256':{n:sha(Path(__file__).with_name(n).read_bytes()) for n in ('build_train_v5.py','build_xss_v3.py','build_small_dataset.py')},
             'skeleton_source_sha256':sha((ROOT/'sentinel/model/skeletons.py').read_bytes())}
    summary['skeleton_groups']={s:dict(Counter(r['class'] for r in {r['skeleton_group_id']:r for r in catalogue+new_catalog if r['assigned_split']==s}.values())) for s in sets}
    (output/'provenance.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'README.md').write_text("""# v5：只補強訓練資料

train594（每類198），test150、Sylius validation150、challenge96原檔凍結，共990筆。三份保留CSV的所有bytes、ID、骨架、標籤不變；舊small-api-v4保留。比例不再是60/20/20，因為只增加train，不能假稱原比例。
新增48組正常／SQLi／XSS配對共144筆，四位置每類各12，依三份API文件選欄位；companyName只放公司名稱，教材字面內容只放搜尋／備註自由文字。新增攻擊依骨架與跨家族原文近似檢查避開全部既有攻擊；排除紀錄見candidate-decisions.csv。
全部仍是離線候選，HTTP=0、業務與攻擊成功未驗證；API型別／enum限制可能拒絕攻擊。沒有新造路徑或ID去填正常長路徑，這個涵蓋缺口仍存在。CASE／JS片段需相應可執行語境，標籤表示來源意圖。
只依已觀察到的錯誤類型策劃一次資料補強；保留集已被檢視，只能作探索性比較，不能宣稱最終泛化。沒有用新評估成績挑案例或調參。原文不正規化，特徵v5=2402維與固定150棵參數不變。Medusa不使用，Sylius只作外部驗證，外部來源與MIT授權維持不變。
"""+'\n```json\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
    return {k:summary[k] for k in ('splits','augmentation','skeleton_groups')}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'sentinel/dataset/small-api-v4')
    p.add_argument('--output',type=Path,default=ROOT/'sentinel/dataset/small-api-v5')
    a=p.parse_args();print(json.dumps(build(a.source,a.output),ensure_ascii=False))
