"""依文件修正正常控制，攻擊從修正後控制重新嵌入相同原文；保留舊版本。"""
import argparse
from collections import Counter,defaultdict
import copy,csv,json,re,sys
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'sentinel/model'))
from data_io import read_rows
from request_input import SENSITIVE
from build_small_dataset import sha,read_documents,field_value,finalize,write_csv
from build_xss_v3 import set_field
from build_train_v5 import flat
from annotate_attack_facets import attack_facets,COLUMN
from document_values import PLACEHOLDER,violations,remove_field,type_names

COMPANIES=['Maple Trading','Cedar Textiles','Harbour Books','River Crafts','North Star Supply','Willow Studio','Seaside Goods','Oak Homeware']
DEPARTMENTS=['Customer Service','Purchasing','Warehouse','Accounting','Retail Sales','Operations']
ADDRESSES=['Apartment 2B','Building C','Floor 3','Unit 5','Reception desk','Rear entrance','Suite 4','Office 6']
DATES=['1988-02-14','1991-07-23','1985-11-08','1995-04-19','1990-09-03','1998-12-21','1987-06-16','1993-03-27']
OPTIONAL_UNKNOWN={'slots','order','association[typeCode]','association[ownerCode]','localeCode for order[translation.name]','productTaxons.taxon.code','taxon'}
FLAGS={'reduce-aggregations','no-aggregations','only-aggregations'}


def evidence_values():
    pools=defaultdict(set);sources=[]
    for platform in ('bagisto','shopware','sylius'):
        for path in sorted((ROOT/'sentinel/local-platforms/reports').glob(platform+'-*.json')):
            data=json.loads(path.read_text(encoding='utf-8-sig'))
            if data.get('outcome')!='passed':continue
            sources.append({'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path.read_bytes()),'recorded_at':data.get('recorded_at')})
            def walk(value):
                if isinstance(value,dict):
                    for key,v in value.items():
                        if key in ('languageId','manufacturerId','propertyIds','productNumber','sku'):
                            for x in (v if isinstance(v,list) else [v]):
                                if isinstance(x,str) and x and '[REDACTED]' not in x:pools[platform,key].add(x)
                    if value.get('@type')=='Product':
                        for key in ('code','name'):
                            if isinstance(value.get(key),str):pools[platform,'product_'+key].add(value[key])
                    for v in value.values():walk(v)
                elif isinstance(value,list):
                    for v in value:walk(v)
            for record in data.get('requests',[]):walk(record.get('response_body'))
    if not pools['shopware','languageId']:raise ValueError('沒有真實語言ID證據，不能隨機捏造')
    return {k:sorted(v) for k,v in pools.items()},sources


def choose(pool,index):return pool[index%len(pool)]


def replacement(platform,location,name,request,index,pools):
    base=name.split('.')[-1]
    if name=='sw-language-id':return choose(pools['shopware','languageId'],index),'historical_platform_language_id'
    if name in ('manufacturer','properties','property-whitelist'):
        pool=pools.get(('shopware','manufacturerId' if name=='manufacturer' else 'propertyIds'),[])
        if pool:return choose(pool,index),'historical_platform_filter_id'
        return None,'omit_optional_unbound_identifier'
    if base in ('companyName','company'):return choose(COMPANIES,index),'document_company_test_values'
    if base=='department':return choose(DEPARTMENTS,index),'document_department_test_values'
    if base=='title':return choose(['Mr','Ms','Dr'],index),'document_title_test_values'
    if base in ('address2','additionalAddressLine1','additionalAddressLine2'):return choose(ADDRESSES,index),'document_address_line_test_values'
    if base in ('phone','phoneNumber'):return choose(['2025550101','2025550102','2025550103','2025550104','2025550105','2025550106'],index),'synthetic_test_phone'
    if base=='dateOfBirth':return choose(DATES,index),'valid_iso_birth_date'
    if base in ('zipcode','postcode'):return choose(['10115','20095','80331','50667','60311','70173','28195','04109'],index),'document_postcode_test_values'
    if base=='provinceName':return None,'nullable_optional_province'
    if base in ('paymentSuccessUrl','paymentFailureUrl','paymentCancelUrl'):
        status={'paymentSuccessUrl':'success','paymentFailureUrl':'failure','paymentCancelUrl':'cancel'}[base]
        return 'http://127.0.0.1:18081/test-payment/'+choose(['web','mobile','checkout'],index)+'/'+status,'local_only_payment_callback_candidate'
    if base in ('term','query','search','translations.name','label') or name=='translations.name':
        pool=pools.get((platform,'product_name' if name=='translations.name' else 'productNumber' if platform=='shopware' else 'sku'),[])
        if not pool:pool=[a+' '+b for a in ('cotton','linen','navy','white','summer','casual','wool','denim') for b in ('shirt','cap','jacket','trousers','scarf','dress','socks','bag')]
        return choose(pool,index),'historical_product_search_text' if (platform,'productNumber') in pools or (platform,'product_name') in pools else 'document_search_test_values'
    if base in ('specialNote','customerComment','notes'):
        return choose(['Please leave the parcel at reception','Please use the side entrance','Please call before delivery','Gift package requested','Please include the receipt','Collect from the service desk'],index),'document_customer_note_test_values'
    return None,'unresolved_no_generic_fallback'


def correct_normal(row,index,ops,pools):
    result=copy.deepcopy(row['input']);key=row['metadata']['platform'],row['input']['method'],row['metadata']['operation_path'];op=ops[key];changes=[]
    for (location,name),spec in op['fields'].items():
        present,old=field_value(result,location,name)
        if not present or SENSITIVE.search(name):continue
        reason=None;delete=False;new=old
        if '〈' in name:
            delete=True;reason='documentation_union_branch_is_not_a_wire_property'
        elif name in FLAGS:
            delete=True;reason='optional_document_live_schema_disagreement_omit_flag'
        elif name=='countryStateId' and old is None:
            delete=True;reason='optional_state_id_unbound_omit_not_fake'
        elif name in OPTIONAL_UNKNOWN and old==PLACEHOLDER:
            delete=True;reason='optional_identifier_or_sorting_not_bound_to_platform'
        elif name=='items[].priceDefinition.type' and old==PLACEHOLDER:
            delete=True;reason='standard_product_uses_platform_price_omit_custom_definition'
        elif old==PLACEHOLDER or name=='sw-language-id':
            new,reason=replacement(key[0],location,name,result,index+int(sha(name)[:6],16),pools)
            if reason=='unresolved_no_generic_fallback':
                if spec['required']=='選填':delete=True;reason='omit_optional_without_semantic_value'
                else:raise ValueError('必填欄位缺少可追溯填值策略：'+str((key,location,name)))
            elif reason.startswith('omit_'):delete=True
        if not reason:continue
        if delete:
            remove_field(result,location,'items[].priceDefinition' if name=='items[].priceDefinition.type' else name)
        else:set_field(result,location,name,new)
        changes.append({'location':location,'parameter':name,'old_value':json.dumps(old,ensure_ascii=False),'new_value':None if delete else json.dumps(new,ensure_ascii=False),
                        'action':'omit' if delete else 'replace','basis':reason,'document':spec['source'],'document_line':spec['line'],'meaning':spec['meaning']})
    if key[0]=='shopware' and '_criteria' in result['query']:
        import base64,gzip,io
        old=result['query']['_criteria']
        allowed={'page','limit','term','query','filter','ids','sort','associations','post-filter','aggregations','fields','grouping','includes','excludes','total-count-mode'}
        criteria={n.removesuffix('[]'):v for n,v in result['query'].items() if n.removesuffix('[]') in allowed}
        raw=json.dumps(criteria,ensure_ascii=False,separators=(',',':')).encode()
        buffer=io.BytesIO()
        with gzip.GzipFile(fileobj=buffer,mode='wb',mtime=0,filename='') as stream:stream.write(raw)
        result['query']['_criteria']=base64.urlsafe_b64encode(buffer.getvalue()).decode().rstrip('=')
        spec=op['fields']['query','_criteria']
        changes.append({'location':'query','parameter':'_criteria','old_value':json.dumps(old),
            'new_value':json.dumps(result['query']['_criteria']),'action':'replace',
            'basis':'document_base64url_gzip_json_of_corrected_criteria','document':spec['source'],'document_line':spec['line'],'meaning':spec['meaning']})
    finalize(result,key[2]);return result,changes


def audit_normals(rows,ops):
    issues=[]
    for r in rows:
        if r['annotation']['proposed_label']!='normal':continue
        key=r['metadata']['platform'],r['input']['method'],r['metadata']['operation_path']
        for (location,name),spec in ops[key]['fields'].items():
            if SENSITIVE.search(name):continue
            present,value=field_value(r['input'],location,name)
            if not present:continue
            for error in violations(value,location,name,spec):
                issues.append({'sample_id':r['sample_id'],'platform':key[0],'api':key[2],'location':location,'parameter':name,'issue':error,'value':json.dumps(value,ensure_ascii=False)})
    return issues


def build(source,output):
    if output.exists():raise ValueError('輸出已存在，不覆寫舊版本')
    ops,docs=read_documents();pools,evidence=evidence_values();all_sets={};changes=[];before_issues=[];after_issues=[];trace=[];omitted=Counter();normal_index=0
    before_hashes={s:sha((source/(s+'.csv')).read_bytes()) for s in ('train','test','validation','challenge')}
    for split in before_hashes:
        original=read_rows(source/(split+'.csv'));before_issues.extend(audit_normals(original,ops))
        groups=defaultdict(list)
        for row in original:groups[row['metadata']['pair_group']].append(row)
        rebuilt={}
        for old_pair,triple in groups.items():
            normal=next(r for r in triple if r['annotation']['proposed_label']=='normal');normal_index+=1
            base,edits=correct_normal(normal,normal_index,ops,pools)
            pair=sha(['document-values-v7',old_pair,base]);normal_id=sha([pair,'normal',base])
            for edit in edits:
                changes.append({'split':split,'old_normal_sample_id':normal['sample_id'],**edit})
                if edit['action']=='omit':omitted[edit['parameter'],edit['basis']]+=1
            for old in triple:
                row=copy.deepcopy(old);label=row['annotation']['proposed_label'];request=copy.deepcopy(base)
                if label!='normal':
                    m=old['metadata'];set_field(request,m['target_location'],m['target_parameter'],m['payload']['value']);finalize(request,m['operation_path'])
                sid=normal_id if label=='normal' else sha([pair,label,request])
                row['sample_id']=sid;row['input']=request
                row['metadata'].update(pair_group=pair,origin='document-v7-rule-corrected-offline',source_sample_id=old['sample_id'],
                    source_pair_group=old_pair,value_rules_revision=1,normal_control_constraints_checked=True,normal_constraint_scope="documented primitive,regex,enum,date,url,min,max; not full schema or business",http_executed=False,business_verified=False)
                if label!='normal':row['metadata']['control_sample_id']=normal_id
                rebuilt[old['sample_id']]=row;trace.append({'split':split,'old_sample_id':old['sample_id'],'new_sample_id':sid,'label':label,'input_changed':request!=old['input']})
        rows=[rebuilt[r['sample_id']] for r in original];all_sets[split]=rows;after_issues.extend(audit_normals(rows,ops))
    if after_issues:raise ValueError('修正後仍違反已可檢查的文件約束：'+json.dumps(after_issues[:8],ensure_ascii=False))
    requests=[sha(r['input']) for rows in all_sets.values() for r in rows]
    if len(requests)!=len(set(requests)):raise ValueError('修正後出現重複請求，需檢視，不自行丟棄或湊數')
    output.mkdir(parents=True)
    for split,rows in all_sets.items():
        values=[]
        for row in rows:
            f=flat(row);f[COLUMN]='；'.join(attack_facets(row));values.append(f)
        write_csv(output/(split+'.csv'),values)
    for name in ('skeleton-catalog.csv','external-payloads.csv','HTTPPARAMS-LICENSE.txt','attack-facets-rules.json'):
        if (source/name).is_file():shutil.copy2(source/name,output/name)
    facet_file=output/'attack-facets-rules.json'
    if facet_file.is_file():
        facet=json.loads(facet_file.read_text(encoding='utf-8'))
        facet['notes']=[n for n in facet.get('notes',[]) if '111' not in n]
        facet['notes'].append('v7已依文件修正正常填值；外部XSS標註疑義仍保留，未修改三類標籤')
        facet_file.write_text(json.dumps(facet,ensure_ascii=False,indent=2),encoding='utf-8')
    write_csv(output/'normal-value-changes.csv',changes);write_csv(output/'source-sample-map.csv',trace);write_csv(output/'normal-rule-violations-before.csv',before_issues)
    coverage=[]
    for key,operation in sorted(ops.items()):
        normal_rows=[r for rs in all_sets.values() for r in rs if r['annotation']['proposed_label']=='normal' and (r['metadata']['platform'],r['input']['method'],r['metadata']['operation_path'])==key]
        for (location,name),spec in operation['fields'].items():
            present=sum(True if name=='（本文）' else field_value(r['input'],location,name)[0] for r in normal_rows)
            coverage.append({'platform':key[0],'method':key[1],'api':key[2],'location':location,'parameter':name,
                'document_type':spec['type'],'document':spec['source'],'document_line':spec['line'],'normal_rows_present':present,
                'status':'documentation_branch_not_a_property' if '〈' in name else 'present' if present else 'not_present_optional_or_unbound'})
    write_csv(output/'document-field-status.csv',coverage)
    (output/'historical-public-values.json').write_text(json.dumps({'language_ids':pools['shopware','languageId'],
        'shopware_manufacturer_ids':pools.get(('shopware','manufacturerId'),[]),
        'shopware_property_ids':pools.get(('shopware','propertyIds'),[]),'sources':evidence,
        'note':'historical passed response values; engine unavailable; no current liveness or ID existence claim'},ensure_ascii=False,indent=2),encoding='utf-8')
    rule_snapshot={'scope':'document primitive/regex/enum/date/url/min-max checks; not full schema/business validation',
        'operations':[{'platform':key[0],'method':key[1],'path':key[2],
        'fields':[dict(spec,location=loc,name=name) for (loc,name),spec in operation['fields'].items()]} for key,operation in sorted(ops.items())]}
    (output/'document-value-rules.json').write_text(json.dumps(rule_snapshot,ensure_ascii=False,indent=2),encoding='utf-8')
    saved=json.loads((source/'provenance.json').read_text(encoding='utf-8'));saved.pop('display_annotation',None)
    saved.update(dataset_revision='v7-document-values',required_feature_version=6,parameter_document_sha256=docs,
        document_value_rules_sha256=sha(rule_snapshot),document_value_rules_hash_format='parsed JSON, sorted keys, UTF-8; not request normalization',
        baseline_csv_sha256=before_hashes,frozen_holdout_sha256={s:sha((output/(s+'.csv')).read_bytes()) for s in ('test','validation','challenge')},
        holdout_change_reason='explicit document/data-quality correction; same split and attack payloads, not byte-identical to old evaluation',
        value_correction={'normal_rows':normal_index,'before_rule_issues':len(before_issues),'after_rule_issues':0,'field_changes':len(changes),
           'historical_evidence':evidence,'current_platform_rechecked':False,'language_ids_confirmed_in_history':pools['shopware','languageId'],
           'omitted_fields':[{'parameter':n,'reason':reason,'normal_rows':c} for (n,reason),c in omitted.items()],
           'sensitive_values_redacted':True,'still_requires_live_business_validation':True},
        source_generators_sha256={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in ('build_rule_values_v7.py','build_small_dataset.py')},
        value_policy_source_sha256=sha((ROOT/'sentinel/model/document_values.py').read_bytes().replace(b'\r\n',b'\n')))
    (output/'provenance.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'README.md').write_text('# v7：依文件修正正常值\n\n原v6閱讀版保留。修正正常控制後重新嵌入完全相同的攻擊payload；標籤、集合與骨架不變，ID另存新舊映射。原始輸入在新版本中是明確修正，不是偷偷正規化。\n\n僅有歷史實測語言ID，Docker引擎未運作，未宣稱現在可用或所有業務已通。未知可選ID不捏造；文件分支不是實際欄位，未知或文件／固定版本規格矛盾的選填欄位另記省略原因。不能再宣稱620個位置全部在請求中同時出現。\n\n'+json.dumps(saved['value_correction'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return {'normal_rows':normal_index,'before_issues':len(before_issues),'after_issues':len(after_issues),'field_changes':len(changes),'omitted':dict(omitted)}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'sentinel/dataset/small-api-v6-annotated')
    p.add_argument('--output',type=Path,default=ROOT/'sentinel/dataset/small-api-v7')
    a=p.parse_args();result=build(a.source,a.output);result['omitted']=len(result['omitted']);print(json.dumps(result,ensure_ascii=False))
