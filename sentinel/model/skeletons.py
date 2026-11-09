"""Versioned grouping signatures for attack fragments, never model-input rewriting.

This is a conservative fragment grammar, not a complete JS/SQL parser or proof
of semantic equivalence. Quoted values/numbers and console output aliases do
not create independent evaluation templates. Decoded views exist only here.
"""
from collections import defaultdict
import hashlib
import html
from _skeleton_html_v1 import HTMLParser
import json
import re
from urllib.parse import unquote
from difflib import SequenceMatcher

VERSION=1
PROTOCOL='document-v4-skeleton-disjoint'
PARSER_ID='cpython-3.11.3-htmlparser-frozen-v1'


def parser_fingerprints():
    from pathlib import Path
    here=Path(__file__).resolve().parent
    return {'id':PARSER_ID,'sha256':{name:hashlib.sha256((here/name).read_bytes()).hexdigest()
            for name in ('_skeleton_html_v1.py','_skeleton_markupbase_v1.py','SKELETON-PYTHON-LICENSE.txt')}}

TOKEN=re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|(?:\d+(?:\.\d+)?)|[a-z_$][\w$]*(?:\.[a-z_$][\w$]*)*|--|/\*|\*/|//|===|!==|==|!=|<=|>=|&&|\|\||[^\s]',re.I)
SQL_WORDS=set('and or not union select null from where order by asc desc as case when then else end collate like is in exists between sleep benchmark length json_extract substring substr extractvalue updatexml cast convert concat char if count distinct true false'.split())
JS_WORDS=set('javascript void alert prompt confirm eval function settimeout setinterval string.fromcharcode console.output'.split())


def analysis_view(value):
    text=value
    for _ in range(3):
        changed=html.unescape(unquote(text))
        changed=re.sub(r'\\u([0-9a-fA-F]{4})|\\x([0-9a-fA-F]{2})',
                       lambda m:chr(int(m.group(1) or m.group(2),16)),changed)
        if changed==text:break
        text=changed
    return text


def lex(value,language):
    text=value.lower()
    if language=='js':
        text=re.sub(r'console\.(?:log|info|debug|warn|error)\b','console.output',text)
        if text.startswith('`${') and text.endswith('}`'):text=text[1:-1]
        # Attack fragments often begin by closing a quote from their embedding context.
        text=re.sub(r'^(?:\\)?["\'](?=\s*[;\)])',' quote_boundary ',text)
    else:
        text=re.sub(r'^([%\s]*)(["\'])(?=\s*(?:\)|;|or\b|and\b|union\b))',r'\1 quote_boundary ',text)
    tokens=[]
    words=SQL_WORDS if language=='sql' else JS_WORDS
    for token in TOKEN.findall(text):
        if len(token)>=2 and token[0] in ('"',"'") and token[-1]==token[0]:tokens.append('LITERAL')
        elif re.fullmatch(r'\d+(?:\.\d+)?',token) or token in ('null','true','false'):tokens.append('LITERAL')
        elif token=='$':tokens.append('$')
        elif re.fullmatch(r'[a-z_$][\w$]*(?:\.[a-z_$][\w$]*)*',token):
            tokens.append(token if token in words or token=='quote_boundary' else 'IDENTIFIER')
        elif token in ('"',"'"):tokens.append('QUOTE')
        else:tokens.append(token)
    return tokens


class Fragment(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.tokens=[];self.script=False;self.tags=0

    def handle_starttag(self,tag,attrs):
        self.tags+=1;items=[]
        for name,value in attrs:
            if name.startswith('on'):
                items.append(['EVENT',lex(value or '', 'js')])
            elif value is not None and re.match(r'^\s*javascript\s*:',value,re.I):
                items.append([name,'javascript',lex(value.split(':',1)[1],'js')])
            else:items.append([name,'PRESENT' if value is None else 'ATTRIBUTE_VALUE'])
        self.tokens.append(['START',tag,sorted(items,key=lambda x:json.dumps(x))])
        if tag=='script':self.script=True

    def handle_endtag(self,tag):
        self.tokens.append(['END',tag]);self.tags+=1
        if tag=='script':self.script=False

    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs);self.handle_endtag(tag)

    def handle_data(self,data):
        if not data.strip():return
        if self.script:self.tokens.append(['JS',lex(data,'js')])
        elif re.search(r'["\'<>();{}$]',data):self.tokens.append(['BOUNDARY',lex(data,'js')])
        else:self.tokens.append(['TEXT'])

    def handle_comment(self,data):
        self.tokens.append(['COMMENT',lex(data,'js') if '#exec' in data else 'COMMENT_TEXT'])


def signature(value,label):
    if not isinstance(value,str):raise ValueError('骨架分組只接受字串輸入')
    view=analysis_view(value)
    if label=='sqli':tree=['SQL',lex(view,'sql')]
    elif label=='xss':
        parser=Fragment()
        try:parser.feed(view);parser.close()
        except Exception:parser.tags=0
        tree=['HTML',parser.tokens] if parser.tags else ['JS_FRAGMENT',lex(view,'js')]
    else:raise ValueError('只有攻擊來源有骨架；正常對照由 pair_group 跟隨')
    return json.dumps(tree,ensure_ascii=False,separators=(',',':'))


def group_catalog(entries):
    """Join equal grammar signatures; also join >=.90 raw-shape siblings.

    The raw similarity edge only applies inside the same class/family. It is
    a conservative extra guard, not a semantic-equivalence decision threshold.
    Connected components ensure transitive siblings cannot escape grouping.
    """
    parent=list(range(len(entries)));seen={}
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(a,b):parent[root(a)]=root(b)
    signatures=[signature(e['value'],e['label']) for e in entries]
    for i,(entry,sig) in enumerate(zip(entries,signatures)):
        key=(entry['label'],sig)
        if key in seen:union(i,seen[key])
        seen[key]=i
    for i,a in enumerate(entries):
        for j in range(i):
            b=entries[j]
            if a['label']==b['label'] and a.get('family') and a.get('family')==b.get('family'):
                if SequenceMatcher(None,analysis_view(a['value']),analysis_view(b['value']),autojunk=False).ratio()>=.90:
                    union(i,j)
    members=defaultdict(list)
    for i in range(len(entries)):members[root(i)].append(i)
    groups={}
    for indices in members.values():
        canonical=json.dumps(sorted({(entries[i]['label'],signatures[i]) for i in indices}),ensure_ascii=False)
        gid='sk1-'+hashlib.sha256(canonical.encode()).hexdigest()[:24]
        for i in indices:groups[i]=gid
    return groups,signatures


def audit_dataset(data_dir, sets, saved):
    """重算完整候選目錄，防止只換 template ID 或骨架標記就跨集合。"""
    import csv
    errors=[]
    path=data_dir/'skeleton-catalog.csv'
    if saved.get('skeleton_parser')!=parser_fingerprints():
        return ['骨架解析器版本／檔案指紋不符，請重新上傳完整新版套件']
    if saved.get('skeleton_rule_version')!=VERSION:
        return ['骨架規則版本不符']
    if not path.is_file():return ['缺少 skeleton-catalog.csv']
    if hashlib.sha256(path.read_bytes()).hexdigest()!=saved.get('skeleton_catalog_sha256'):
        errors.append('骨架目錄 SHA256 不符')
    with path.open(encoding='utf-8-sig',newline='') as f:catalog=list(csv.DictReader(f))
    if not catalog:return errors+['骨架目錄為空']
    entries=[dict(e,label=e['class']) for e in catalog]
    groups,signatures=group_catalog(entries)
    lookup={};locations=defaultdict(set)
    for i,e in enumerate(catalog):
        if e['skeleton_group_id']!=groups[i] or e['skeleton_signature']!=signatures[i]:
            errors.append('骨架目錄無法由原文重算')
        locations[groups[i]].add(e['assigned_split'])
        key=e['class'],e['value'],e['template'],e['source']
        lookup[key]=e
    if any(len(v)>1 for v in locations.values()):errors.append('骨架目錄含跨集合近似變體')
    # Also recompute observed rows independently, so a catalogue omission cannot hide overlap.
    observed=[];observed_splits=[]
    for split,rows in sets.items():
        for row in rows:
            meta=row['metadata'];payload=meta.get('payload')
            if meta.get('evaluation_protocol')!=PROTOCOL:
                errors.append('資料列與骨架實驗規則不符：'+split)
            if not payload:
                if row['annotation'].get('proposed_label',row['annotation'].get('label'))!='normal':
                    errors.append('攻擊列缺少 payload')
                continue
            label=row['annotation'].get('label',row['annotation'].get('proposed_label'))
            entry=lookup.get((label,payload['value'],payload['template'],payload['source']))
            if entry is None or entry['assigned_split']!=split or entry['excluded_local_overlap']=='True':
                errors.append('攻擊原文不在該集合的骨架目錄：'+split)
            elif any(meta.get(k)!=entry[k] or payload.get(k)!=entry[k] for k in ('skeleton_group_id','skeleton_signature')):
                errors.append('資料列骨架標記與重算目錄不符：'+split)
            if meta.get('skeleton_rule_version')!=VERSION or payload.get('skeleton_rule_version')!=VERSION:
                errors.append('資料列骨架版本不符：'+split)
            observed.append(dict(payload,label=label));observed_splits.append(split)
    actual,_=group_catalog(observed);locations=defaultdict(set)
    for i,split in enumerate(observed_splits):locations[actual[i]].add(split)
    if any(len(v)>1 for v in locations.values()):errors.append('實際資料含跨集合骨架／近似變體')
    return sorted(set(errors))
