"""Small document-driven offline corpus: seen families, unseen contexts, fresh external holdout."""
from collections import Counter, defaultdict
import argparse
import copy
import csv
import io
import itertools
import json
from pathlib import Path
import random
import re
import sys
from urllib.request import urlopen
from build_small_dataset import ROOT, COMMIT, SOURCE, SENSITIVE, sha, read_documents, finalize, put, field_value, write_csv

PROTOCOL = 'document-v3-seen-families-heldout-templates'
LOCATIONS = ('header','body','query','path')
QUOTAS = {'train':150,'test':50,'validation':50,'challenge':32}
FIRST = ['Emily','Daniel','Olivia','Lucas','Sophia','Ethan','Mia','Noah','Amelia','Liam','Isabella','Henry','Ava','James','Charlotte','Benjamin','Evelyn','Oliver','Harper','Elijah']
LAST = ['Chen','Lin','Martin','Wang','Taylor','Wilson','Lee','Brown','Clark','Lewis','Walker','Young','Allen','King','Scott','Green','Baker','Adams','Hill','Moore']
XSS = {
 'xss.script': [
  '<script>console.info("catalog")</script>', '<script>window.name="demo"</script>',
  '<script>String.fromCharCode(88,83,83)</script>', '<ScRiPt>console.info("review")</ScRiPt>',
  '<script>console.log("product")</script>', '<script>document.title="sample"</script>'],
 'xss.event': [
  '<img src=x onerror="console.info(\'image\')">', '<svg onload="console.info(\'icon\')"></svg>',
  '" autofocus onfocus="console.info(\'field\')" data-note="', '<input onmouseover="console.info(\'hover\')">',
  '<details open ontoggle="console.info(\'details\')">', '<video onerror="console.log(\'media\')"></video>'],
 'xss.url': [
  'javascript:console.info("preview")', 'javascript:window.name="item"',
  '<a href="javascript:console.info(\'link\')">item</a>', '<iframe src="javascript:console.info(\'frame\')"></iframe>',
  'javascript:console.log("checkout")', '<form action="javascript:console.info(\'submit\')"></form>'],
 'xss.js-string': [
  '";console.info("note");//', "';console.info('order');//", '\\";window.name="review";//',
  "');console.info('item');//", '";console.log("cart");//', "';document.title='shipping';//"],
 'xss.js-template': [
  '${console.info("template")}', '${String.fromCharCode(88,83,83)}', '${window.name="cart"}',
  '`${console.info("interpolation")}`', '${console.log("address")}', '${document.title="payment"}']}
UNSEEN = {
 'xss.entity-encoded': ['&lt;img src=x onerror=console.info(&quot;entity&quot;)&gt;',
   '&#60;script&#62;console.info("encoded")&#60;/script&#62;',
   '&#x3c;svg onload=console.info("hex")&#x3e;&#x3c;/svg&#x3e;',
   '&lt;a href=&quot;javascript:console.info(1)&quot;&gt;sample&lt;/a&gt;'],
 'xss.js-comment-boundary': ['*/console.info("comment");/*', '*/window.name="sample";/*',
   '\nconsole.info("line-comment");//', '\nwindow.name="line-context";//']}
BENIGN = {
 'train': ['HTML reference: <script> tag documentation', '文件文字：onload= 與 onerror= 的差異',
  'Reference text for the javascript: URI scheme', 'Template syntax guide: ${customer.name}',
  'JavaScript 課程範例：console.info("hello")', 'Notes on string delimiters: "; and //',
  'HTML 文件範例：<b>棉質</b>', 'Encoding reference: %3C and &lt; as literal text'],
 'test': ['A book explaining the <script> element', '查詢 onfocus= 事件的參考資料',
  '教材：javascript: 網址格式解析', 'Find documentation for ${product.name}',
  'Course topic: console.log("example")', '筆記包含 \' ; // 這些符號',
  '標籤字面內容 <em>尺寸</em>', 'Examples of %3E and &#62; in an encoding guide'],
 'challenge': ['註解語法課程與程式碼範例', 'HTML entity 編碼教學筆記', '字元 # $ ` { } 的字面用途']}


def read_reference():
    rows=[]
    for split in ('train','test','validation'):
        with (ROOT/'sentinel/dataset/small-api-v2'/f'{split}.csv').open(encoding='utf-8-sig',newline='') as f:
            rows += [json.loads(r['完整紀錄JSON']) for r in csv.DictReader(f)]
    return rows


def allocate(ops):
    result={}
    fixed={('bagisto','GET','/products/{id}'):'train',
           ('bagisto','PUT','/customer-addresses/{id}'):'test',
           ('shopware','POST','/product/{productId}'):'train',
           ('shopware','POST','/product-listing/{categoryId}'):'challenge'}
    for platform in ('bagisto','shopware'):
        keys=sorted(k for k in ops if k[0]==platform)
        random.Random('v3-op-'+platform).shuffle(keys)
        chosen={k:s for k,s in fixed.items() if k in keys}
        for split in ('test','challenge'):
            for key in keys:
                if sum(s==split for s in chosen.values())>=4:break
                if key not in chosen:chosen[key]=split
        result.update({k:chosen.get(k,'train') for k in keys})
    result.update({k:'validation' for k in ops if k[0]=='sylius'})
    return result


def set_field(req, location, name, value):
    target=req[{'header':'headers','body':'body','query':'query','path':'path_parameters'}[location]]
    if location=='body':put(target,name,value)
    else:target[name]=value


def targets(req, op):
    options=defaultdict(list)
    for (loc,name),spec in op['fields'].items():
        if name=='（本文）' or SENSITIVE.search(name) or any(t in spec['type'] for t in ('object','array')):
            continue
        if field_value(req,loc,name)[0]:options[loc].append(name)
    for loc in options:
        options[loc].sort(key=lambda n:(not ('string' in op['fields'][loc,n]['type'] and '固定值：' not in op['fields'][loc,n]['values']),n))
    return options


def free_text(req, op):
    # Genuine document business fields, never language/currency/authentication headers or IDs.
    return [(loc,n) for (loc,n),spec in op['fields'].items()
        if loc in ('query','body') and n.split('.')[-1] in ('search','query','term','notes','specialNote','label','description')
        and 'string' in spec['type'] and '固定值：' not in spec['values']
        and field_value(req,loc,n)[0] and isinstance(field_value(req,loc,n)[1],str)]


def identity(value, first, last):
    if isinstance(value,dict):
        out={}
        for key,child in value.items():
            k=key.lower().replace('_','')
            if k=='firstname' and isinstance(child,str):out[key]=first
            elif k=='lastname' and isinstance(child,str):out[key]=last
            elif k in ('email','username') and isinstance(child,str):out[key]=first.lower()+'.'+last.lower()+'@example.org'
            else:out[key]=identity(child,first,last)
        return out
    if isinstance(value,list):return [identity(v,first,last) for v in value]
    return value


def external_pools(reference):
    raw=urlopen(SOURCE+'/payload_full.csv',timeout=60).read()
    original=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    old={r['metadata']['payload']['value'] for r in reference if r['metadata'].get('payload')
         and r['metadata']['payload'].get('source')=='httpParamsDataset'}
    pools={}
    for attack_type,label in [('norm','normal'),('sqli','sqli'),('xss','xss')]:
        options={}
        for index,row in enumerate(original,2):
            value=row['payload']
            if row['attack_type']==attack_type and value not in old and 0<len(value)<=256 and not any(ord(c)<32 for c in value):
                options.setdefault(value,{'value':value,'family':None,'template':f'external:{index}',
                                         'source':'httpParamsDataset','commit':COMMIT,'record':index})
        options=list(options.values());random.Random('v3-external-'+label).shuffle(options)
        pools[label]=options[:24]
    return pools,{r['payload'] for r in original},{'commit':COMMIT,'url':SOURCE+'/payload_full.csv',
            'sha256':sha(raw),'excluded_previous_external_values':len(old),'selection':'seeded 24 per class; <=256 chars; no controls; no score-based filtering'}


def case_pools(external_values):
    pools={s:{'xss':[],'sqli':[]} for s in ('train','test','challenge')}
    for family,values in XSS.items():
        for index,value in enumerate(values):
            if value in external_values:raise ValueError('本地 XSS 與外部全檔重複，請換不同模板')
            split='train' if index<4 else 'test'
            pools[split]['xss'].append({'value':value,'family':family,'template':family+':'+str(index),
                                       'source':'local_curated_v3'})
    for family,values in UNSEEN.items():
        for index,value in enumerate(values):
            if value in external_values:raise ValueError('保留挑戰原文與外部重複')
            pools['challenge']['xss'].append({'value':value,'family':family,'template':family+':'+str(index),
                                             'source':'local_curated_v3','requires_specific_render_context':True})
    families=defaultdict(dict)
    with (ROOT/'sentinel/dataset/scenario-catalog.csv').open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            case=json.loads(row['完整情境JSON']);value=case.get('value')
            if case['proposed_label']=='sqli' and isinstance(value,str) and value not in external_values and case['family_id']!='sql.structure':
                families[case['family_id']].setdefault(value,case)
    for family,items in sorted(families.items()):
        values=sorted(items)
        if len(values)<2:continue
        for index,value in enumerate(values):
            split='test' if index==len(values)-1 else 'train'
            pools[split]['sqli'].append({'value':value,'family':family,'template':items[value]['base_case_id'],
                                         'source':'existing_scenario_catalog'})
    for index,value in enumerate(['CASE WHEN length(\'demo\')=4 THEN name ELSE id END',
                                  'name,(SELECT 1)', 'name COLLATE utf8mb4_general_ci',
                                  "(SELECT CASE WHEN 'a'='a' THEN 1 ELSE 2 END)"]):
        if value in external_values:raise ValueError('SQL 挑戰與外部原文重複')
        pools['challenge']['sqli'].append({'value':value,'family':'sql.structure','template':f'sql.structure.v3:{index}',
                                           'source':'local_curated_v3','requires_specific_render_context':True})
    return pools


def build(output):
    if output.exists():raise ValueError('輸出已存在，不能覆寫基準')
    ops,hashes=read_documents();reference=read_reference();assignment=allocate(ops)
    ext,external_values,ext_source=external_pools(reference);cases=case_pools(external_values)
    bases=[r for r in reference if r['metadata']['variant'] in ('document_baseline','exclusive_session_cookie_alternative')]
    assert {(r['metadata']['platform'],r['input']['method'],r['metadata']['operation_path']) for r in bases}==set(ops)
    candidates=defaultdict(list);seen_controls=set()
    for base in bases:
        bm=base['metadata'];key=bm['platform'],base['input']['method'],bm['operation_path'];split=assignment[key]
        optional=[n for (loc,n),spec in ops[key]['fields'].items() if loc=='header' and spec['required']=='選填' and not SENSITIVE.search(n)]
        for variant in range(48):
            req=copy.deepcopy(base['input'])
            req['body']=identity(req['body'],FIRST[variant%20],LAST[(variant//20+variant)%20])
            req['query']=identity(req['query'],FIRST[variant%20],LAST[(variant//20+variant)%20])
            if variant:
                for i,n in enumerate(optional):
                    if (variant>>i)&1:req['headers'].pop(n,None)
                for (loc,n),spec in ops[key]['fields'].items():
                    if loc in ('query','body') and n in ('page','p','limit','per_page') and field_value(req,loc,n)[0] and 'integer' in spec['type']:
                        set_field(req,loc,n,1+((variant//5)%7 if n in ('limit','per_page') else variant%5))
            hard=None;free=free_text(req,ops[key])
            if variant and free:
                if split=='validation':entry=ext['normal'][variant%len(ext['normal'])]
                else:entry={'value':BENIGN[split][variant%len(BENIGN[split])],'source':'benign_document_text_v3'}
                set_field(req,*free[variant%len(free)],entry['value']);hard=entry
            finalize(req,key[2]);fingerprint=sha(req)
            if fingerprint in seen_controls:continue
            options=targets(req,ops[key])
            if not options:continue
            seen_controls.add(fingerprint)
            candidates[split].append({'request':req,'key':key,'base':base,'targets':options,
                'must':variant==0,'hard_negative':hard,'variant':variant})
    rows=[];used_requests=set();use=Counter();family_use=Counter();locstats={}
    for split,budget in QUOTAS.items():
        available=list(candidates[split]);random.Random('v3-controls-'+split).shuffle(available)
        quotas={loc:budget//4+(i<budget%4) for i,loc in enumerate(LOCATIONS)}
        selected=[];selected_ids=set();counts=Counter()
        # Always retain the full document baselines (including exclusive context variants).
        for candidate in sorted((c for c in available if c['must']),key=lambda c:str(c['key'])):
            eligible=[loc for loc in LOCATIONS if loc in candidate['targets'] and counts[loc]<quotas[loc]]
            loc=min(eligible,key=lambda l:sum(l in c['targets'] for c in available))
            selected.append((candidate,loc));selected_ids.add(id(candidate));counts[loc]+=1
        # Fill scarce path/query targets first, with independent controls rather than row duplication.
        order=sorted(LOCATIONS,key=lambda l:sum(l in c['targets'] for c in available))
        for loc in order:
            for candidate in available:
                if counts[loc]>=quotas[loc]:break
                if id(candidate) in selected_ids or loc not in candidate['targets']:continue
                selected.append((candidate,loc));selected_ids.add(id(candidate));counts[loc]+=1
            if counts[loc]!=quotas[loc]:raise ValueError(f'{split}/{loc} 可用文件情境不足：{counts[loc]}/{quotas[loc]}')
        locstats[split]=dict(counts)
        for candidate,loc in selected:
            key=candidate['key'];target=(loc,candidate['targets'][loc][use[split,key,loc]%len(candidate['targets'][loc])]);use[split,key,loc]+=1
            normal_req=candidate['request'];pair=sha(['v3',split,normal_req]);normal_id=sha([pair,'normal',normal_req])
            reference_path=candidate['base']['metadata']['historical_source_report']
            common={'platform':key[0],'operation_path':key[2],'split':split,'evaluation_protocol':PROTOCOL,
                    'origin':'document-v3-offline','request_input_version':3,'http_executed':False,
                    'raw_target_captured':False,'raw_body_captured':False,'session_group':None,
                    'source_evidence':None,'historical_value_reference':reference_path,'source_template_group':sha(key),
                    'pair_group':pair,'schema_validity':'not_validated','business_verified':False,
                    'parameter_document':f'sentinel/analysis/selected-api-contracts/{key[0]}/API_parameters.md',
                    'benign_content_context':candidate['hard_negative'],'product_prerequisites':'inherited v2 offline candidate; IDs/conditional product types not currently verified'}
            normal={'sample_id':normal_id,'input':copy.deepcopy(normal_req),'annotation':{'proposed_label':'normal',
                     'label_basis':'document business field / benign literal content intent; not live business success'},
                    'metadata':{**common,'payload':None,'target_location':None,'target_parameter':None,'template_id':None}}
            if sha(normal_req) in used_requests:raise ValueError('正常控制重複')
            rows.append(normal);used_requests.add(sha(normal_req))
            for label in ('sqli','xss'):
                pool=ext[label] if split=='validation' else cases[split][label]
                ordered=sorted(pool,key=lambda p:(family_use[split,label,p.get('family')],use[split,label,p['template']],p['template']))
                chosen=None
                for payload in ordered:
                    if loc=='header' and any(ord(c)<32 or ord(c)==127 for c in payload['value']):continue
                    req=copy.deepcopy(normal_req);set_field(req,*target,payload['value']);finalize(req,key[2])
                    if sha(req) not in used_requests:chosen=payload;break
                if chosen is None:raise ValueError('模板不足以產生不同請求，不用換尾數補數')
                use[split,label,chosen['template']]+=1;family_use[split,label,chosen.get('family')]+=1
                metadata={**common,'target_location':loc,'target_parameter':target[1],'payload':chosen,
                          'template_id':sha([label,chosen['template']]),'control_sample_id':normal_id,
                          'value_may_violate_document_constraints':True}
                rows.append({'sample_id':sha([pair,label,req]),'input':req,
                             'annotation':{'proposed_label':label,'label_basis':'payload source/intent; context may be invalid or rejected; no exploit success claim'},'metadata':metadata})
                used_requests.add(sha(req))
    # Prove isolation of raw payload templates, API operations and complete requests.
    for a,b in itertools.combinations(QUOTAS,2):
        for kind in ('template','value'):
            left={r['metadata']['payload'][kind] for r in rows if r['metadata']['split']==a and r['metadata']['payload']}
            right={r['metadata']['payload'][kind] for r in rows if r['metadata']['split']==b and r['metadata']['payload']}
            if left&right:raise ValueError(f'{a}/{b} 攻擊 {kind} 重複')
    coverage=[]
    for key,op in sorted(ops.items()):
        chosen=[r for r in rows if (r['metadata']['platform'],r['input']['method'],r['metadata']['operation_path'])==key]
        for (loc,n),spec in op['fields'].items():
            present=sum((True if n=='（本文）' else field_value(r['input'],loc,n)[0]) for r in chosen)
            if not present:raise ValueError(f'文件欄位遺漏：{key} {loc}/{n}')
            coverage.append({'平台':key[0],'集合':assignment[key],'方法':key[1],'API':key[2],'位置':loc,'參數':n,
                             '文件型別':spec['type'],'存在筆數':present,'文件':spec['source'],'行號':spec['line'],'狀態':'離線候選，未實機驗證'})
    output.mkdir(parents=True)
    stats={}
    for split in QUOTAS:
        data=[r for r in rows if r['metadata']['split']==split]
        flat=[{'樣本ID':r['sample_id'],'平台':r['metadata']['platform'],'集合':split,'類別':r['annotation']['proposed_label'],
               '方法':r['input']['method'],'API':r['metadata']['operation_path'],
               'Header_JSON':json.dumps(r['input']['headers'],ensure_ascii=False),
               'Query_JSON':json.dumps(r['input']['query'],ensure_ascii=False),'Body_JSON':json.dumps(r['input']['body'],ensure_ascii=False),
               'Path':r['input']['path'],'原始Query':r['input']['raw_query'],'原始Body':r['input']['raw_body'],
               'Payload原文':(r['metadata']['payload'] or {}).get('value'),
               '完整紀錄JSON':json.dumps(r,ensure_ascii=False)} for r in data]
        write_csv(output/(split+'.csv'),flat)
        stats[split]={'rows':len(data),'labels':dict(Counter(r['annotation']['proposed_label'] for r in data)),
                      'platforms':dict(Counter(r['metadata']['platform'] for r in data)),
                      'xss_unique_payloads':len({r['metadata']['payload']['value'] for r in data if r['annotation']['proposed_label']=='xss'}),
                      'xss_families':dict(Counter(r['metadata']['payload'].get('family') or 'external_unclassified' for r in data if r['annotation']['proposed_label']=='xss')),
                      'attack_locations_per_class':locstats[split],
                      'normal_literal_controls':sum(bool(r['metadata']['benign_content_context']) for r in data if r['annotation']['proposed_label']=='normal')}
    write_csv(output/'field-coverage.csv',coverage)
    write_csv(output/'external-payloads.csv',[{'class':label,**p} for label,pool in ext.items() for p in pool])
    license_text=(ROOT/'sentinel/dataset/small-api-v2/HTTPPARAMS-LICENSE.txt').read_text(encoding='utf-8')
    (output/'HTTPPARAMS-LICENSE.txt').write_text(license_text,encoding='utf-8')
    summary={'evaluation_protocol':PROTOCOL,'main_ratio':'60:20:20','extra_challenge_is_not_part_of_ratio':True,
             'splits':stats,'parameter_document_sha256':hashes,'document_fields':len(coverage),'api_operations':len(ops),
             'external_source':ext_source,'http_executed':0,'medusa_included':False,
             'source_generators_sha256':{n:sha((Path(__file__).with_name(n)).read_bytes()) for n in ['build_xss_v3.py','build_small_dataset.py']},
             'baseline_csv_sha256':{s:sha((ROOT/'sentinel/dataset/small-api-v2'/f'{s}.csv').read_bytes()) for s in ['train','test','validation']}}
    (output/'provenance.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'README.md').write_text('# API 文件導向離線資料 v3\n\n'
       '主實驗 train/test/validation=450/150/150（60/20/20），另有96筆 challenge。所有集合三類等量；Medusa 不參與。\n\n'
       'train/test 是相同來源家族、不同 payload 模板及 API 操作；challenge 保留未見的實體編碼／JS註解邊界與 SQL 結構語境。'
       '這是明確保留的語法／語境家族，不保證所有未知攻擊都涵蓋。validation 僅 Sylius，外部原文避開 v2 曾選的輸入，未依模型分數挑選。\n\n'
       '四種位置每類分配相近，但各 API 僅使用文件宣告的位置。正常程式碼文字只填搜尋／備註等適合的自由文字欄，'
       '不填認證、語言、貨幣等欄來假造正常。完整參數覆蓋表含620個位置；620不是獨立請求數。\n\n'
       '全部仍是離線生成請求，HTTP未執行。繼承 v2 的條件商品／自訂欄位／null關聯與歷史ID限制；'
       '攻擊值也可能不符型別／enum／長度。所有正常業務成功、儲存型／DOM行為及攻擊成功均未宣稱。'
       '不正規化原文，僅作JSON／URL傳輸序列化，憑證遮蔽。\n\n'
       'metadata 中 historical_value_reference 只是歷史值來源，不是假造的 session；source_template_group、pair_group 和攻擊模板保留相依性。'
       '同家族可跨一般 train/test，不同模板不可跨；真實session與原文重複仍嚴格隔離。\n\n'
       '固定種子選樣，不依 test/validation/challenge 成績調參。舊 v2 資料／v4 特徵及診斷保留。\n\n```json\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'sentinel/dataset/small-api-v3')
    print(json.dumps(build(p.parse_args().output),ensure_ascii=False))
