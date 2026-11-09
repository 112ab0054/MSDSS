"""按保守骨架關聯整組分割；使用原有文件欄位與請求組裝器，不改寫原文。"""
from collections import defaultdict, Counter
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'model'))
import build_xss_v3 as v3
from skeletons import PROTOCOL, VERSION, group_catalog, parser_fingerprints


def allocate_catalog(local, external):
    entries=[dict(p,label=label,origin_split=split) for split,pools in local.items()
             for label,pool in pools.items() for p in pool]
    entries += [dict(p,label=label,origin_split='validation') for label,pool in external.items()
                if label!='normal' for p in pool]
    groups,signatures=group_catalog(entries)
    members=defaultdict(list)
    for i,e in enumerate(entries):members[groups[i]].append(i)
    assigned={};reasons={}
    for gid,indices in members.items():
        origins={entries[i]['origin_split'] for i in indices}
        if 'validation' in origins:assigned[gid]='validation';reasons[gid]='external_validation_reserved'
        elif 'challenge' in origins:assigned[gid]='challenge';reasons[gid]='context_challenge_reserved_with_siblings'
    for label in ('sqli','xss'):
        eligible=sorted(g for g,indices in members.items() if g not in assigned and entries[indices[0]]['label']==label)
        if len(eligible)<2:raise ValueError('可分配骨架不足：'+label)
        # A fixed hash order, not evaluation scores, determines the 3:1 group allocation.
        test_count=max(1,round(len(eligible)/4))
        for i,gid in enumerate(eligible):
            assigned[gid]='test' if i<test_count else 'train';reasons[gid]='fixed_hash_group_partition'
    cases={s:{l:[] for l in ('sqli','xss')} for s in ('train','test','challenge')}
    ext={l:[] for l in external};ext['normal']=[dict(p,skeleton_group_id=None,skeleton_signature=None,skeleton_rule_version=None) for p in external['normal']]
    catalogue=[]
    for i,e in enumerate(entries):
        gid=groups[i];split=assigned[gid]
        excluded=split=='validation' and e['origin_split']!='validation'
        payload={k:v for k,v in e.items() if k not in ('label','origin_split')}
        payload.update(skeleton_group_id=gid,skeleton_signature=signatures[i],skeleton_rule_version=VERSION)
        if not excluded:
            (ext[e['label']] if split=='validation' else cases[split][e['label']]).append(payload)
        catalogue.append({'class':e['label'],'value':e['value'],'family':e.get('family'),
                          'template':e['template'],'source':e['source'],'origin_split':e['origin_split'],
                          'assigned_split':split,'excluded_local_overlap':excluded,
                          'assignment_reason':reasons[gid],'skeleton_group_id':gid,
                          'skeleton_signature':signatures[i],'skeleton_rule_version':VERSION})
    return cases,ext,catalogue


def build(output):
    if output.exists():raise ValueError('輸出已存在，不能覆寫基準')
    external,values,source=v3.external_pools(v3.read_reference())
    cases,external,catalogue=allocate_catalog(v3.case_pools(values),external)
    # The original API allocation and matched triples preserve all 620 documented positions.
    summary=v3.build(output,selected_cases=cases,selected_external=(external,values,source),protocol=PROTOCOL,version=4)
    v3.write_csv(output/'skeleton-catalog.csv',catalogue)
    summary.update(skeleton_rule_version=VERSION, skeleton_parser=parser_fingerprints(),
                   skeleton_catalog_sha256=v3.sha((output/'skeleton-catalog.csv').read_bytes()),
                   skeleton_groups={s:dict(Counter(c['class'] for c in {c['skeleton_group_id']:c for c in catalogue if c['assigned_split']==s}.values())) for s in v3.QUOTAS},
                   excluded_local_overlaps=sum(c['excluded_local_overlap'] for c in catalogue),
                   baseline='small-api-v3 unchanged; raw-template/seen-family comparison only')
    summary['source_generators_sha256'].update({n:v3.sha(Path(__file__).with_name(n).read_bytes()) for n in ['build_skeleton_v4.py']})
    summary['skeleton_source_sha256']=v3.sha((Path(__file__).resolve().parents[1]/'model/skeletons.py').read_bytes())
    (output/'provenance.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'README.md').write_text("""# API 文件導向離線資料 v4：骨架分組

train/test/validation=450/150/150（60/20/20），另有96筆 challenge。三類等量，62個 API、620個文件欄位位置。
Bagisto/Shopware 用於 train/test；Sylius 僅 validation，結合固定版本 httpParamsDataset 原文；Medusa 不參與。
全部是離線候選，HTTP 未執行，不能宣稱平台流程或攻擊成功。繼承 v2 的歷史ID與條件商品限制。

先對所有本地／外部攻擊建立骨架關聯，取連通群後才分配集合。字串、數字、console 輸出函式變體、
大小寫、常見百分比／HTML實體／JS跳脫包裝只在輔助分析視圖合併；原始請求與模型輸入不正規化。
同類同家族原文相似度達0.90也保守合併。這是片段語法規則，不是完整 SQL/JS AST 或所有語意等價的證明。
跨家族／跨平台相同骨架也合併。skeleton-catalog.csv 列出原始來源、簽章、分配與排除原因；不進入模型。

外部骨架優先保留 validation；重疊本地值排除，不移動 Sylius 至訓練。
原 challenge 的骨架及其本地兄弟全部保留 challenge；其餘骨架依固定雜湊排序約3:1分 train/test，
不依模型分數選資料。challenge 現為保留語境群，不能宣稱所有家族／編碼從未出現。
正常對照與兩類攻擊依 pair_group 同集合，API來源／模板關聯仍保留。骨架可跨多個配對，群數不是請求數。

沿用原有文件組裝器，保留全部文件基準與互斥 header 變體、四種輸入位置與正常自由文字控制。
參數可能不符 enum／型別，標籤表示來源意圖。保持特徵v5（2402維）與150棵、深度3、學習率0.05。
舊 small-api-v3 保留為近似變體基準，不能以舊97.33%代表未見骨架效果。
"""+'\n```json\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n```\n',encoding='utf-8')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=v3.ROOT/'sentinel/dataset/small-api-v4')
    result=build(p.parse_args().output)
    print(json.dumps({k:result[k] for k in ('evaluation_protocol','skeleton_groups','excluded_local_overlaps')},ensure_ascii=False))
