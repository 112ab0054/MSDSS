"""文件約束檢查與正常候選填值；不把格式通過當業務成功。"""
from datetime import date
import json
import re

PLACEHOLDER='MSDSS cotton'

def type_names(spec):
    return set(re.findall(r'\b(?:string|integer|number|boolean|object|array|null)\b',spec['type']))


def pattern(spec):
    m=re.search(r'正規(?:表達|表示)式：`([^`]+)`',spec['values'])
    if not m:return None
    value=m[1]
    try:
        parsed=json.loads(value)
        if isinstance(parsed,str):value=parsed
    except ValueError:pass
    return value


def constants(spec):
    text=spec['values']
    if '固定值：' not in text:return []
    part=re.split(r'<br>|預設值：|；',text.split('固定值：',1)[1])[0]
    result=[]
    for value in re.findall(r'`([^`]+)`',part):
        try:value=json.loads(value)
        except ValueError:pass
        result.append(str(value).lower() if isinstance(value,bool) else str(value))
    return result


def violations(value,location,name,spec):
    if value=='[REDACTED]':return []
    result=[];types=type_names(spec)
    if types:
        fits=any((t=='null' and value is None) or (t=='string' and isinstance(value,str)) or
            (t=='integer' and type(value)==int) or (t=='number' and type(value) in (int,float)) or
            (t=='boolean' and type(value)==bool) or (t=='object' and isinstance(value,dict)) or
            (t=='array' and isinstance(value,list)) for t in types)
        # URL/header scalar values are textual on the wire; body types remain strict.
        if location=='body' and not fits:result.append('type')
    regex=pattern(spec)
    if regex and value is not None and not re.fullmatch(regex,str(value)):result.append('pattern')
    choices=constants(spec)
    if choices and not isinstance(value,(dict,list)) and (str(value).lower() if type(value)==bool else str(value)) not in choices:result.append('enum')
    if choices and name in ('sort','sort[]') and isinstance(value,list):
        if any(isinstance(v,dict) and str(v.get('order','ASC')) not in choices for v in value):result.append('sort_order_enum')
    if type(value) in (int,float):
        for label,op in [('最小值：',lambda v,b:v<b),('最大值：',lambda v,b:v>b)]:
            m=re.search(label+r'`?(-?\d+(?:\.\d+)?)',spec['values'])
            if m and op(value,float(m[1])):result.append(label[:-1])
    if isinstance(value,str) and value!=PLACEHOLDER:
        maximum=re.search(r'最多字元數：`?(\d+)',spec['values'])
        if maximum and len(value)>int(maximum[1]):result.append('max_length')
        if 'base64url(gzip(json_encode(criteria)))' in spec['values']:
            try:
                import base64,gzip,io
                if not re.fullmatch(r'[A-Za-z0-9_-]+={0,2}',value):raise ValueError('invalid base64url')
                data=base64.urlsafe_b64decode(value+'='*((-len(value))%4))
                with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:decoded=stream.read(262145)
                if len(decoded)>262144 or not isinstance(json.loads(decoded),dict):raise ValueError('invalid criteria')
            except (ValueError,OSError,EOFError):result.append('compressed_criteria_format')
        if 'date' in spec['values'] and 'date-time' not in spec['values']:
            try:date.fromisoformat(value)
            except ValueError:result.append('date')
        if name.split('.')[-1].lower() in ('email','username') and '電子郵件' in spec['meaning']:
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):result.append('email')
        if (re.search(r'(?:Url|URL|_url)$',name) or '格式：`uri`' in spec['values']) and not re.match(r'^https?://[^/\s]+(?:/|$)',value):result.append('url')
    if value==PLACEHOLDER:result.append('generic_placeholder')
    return result


def remove_field(request,location,name):
    if location!='body':request[{'header':'headers','query':'query','path':'path_parameters'}[location]].pop(name,None);return
    parts=name.split('.');cursor=request['body']
    for part in parts[:-1]:
        key=part.removesuffix('[]')
        if not isinstance(cursor,dict) or key not in cursor:return
        cursor=cursor[key]
        if part.endswith('[]'):
            if not isinstance(cursor,list) or not cursor:return
            cursor=cursor[0]
    if isinstance(cursor,dict):cursor.pop(parts[-1].removesuffix('[]'),None)


def request_field(request,location,name):
    value=request[{'header':'headers','query':'query','path':'path_parameters','body':'body'}[location]]
    if location!='body':return (name in value,value.get(name))
    for part in name.split('.'):
        key=part.removesuffix('[]')
        if not isinstance(value,dict) or key not in value:return False,None
        value=value[key]
        if part.endswith('[]'):
            if not isinstance(value,list) or not value:return False,None
            value=value[0]
    return True,value


def audit_document_values(data_dir,sets,expected_rules_sha256=None):
    from request_input import SENSITIVE
    path=data_dir/'document-value-rules.json'
    if not path.is_file():return ['缺少v7文件填值規則快照']
    saved=json.loads(path.read_text(encoding='utf-8-sig'))
    if expected_rules_sha256 is not None:
        import hashlib
        actual=hashlib.sha256(json.dumps(saved,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        if actual!=expected_rules_sha256:return ['v7文件填值規則快照指紋不符']
    ops={(o['platform'],o['method'],o['path']):o['fields'] for o in saved['operations']}
    errors=[]
    for split,rows in sets.items():
        count=0
        for row in rows:
            if row['annotation'].get('label',row['annotation'].get('proposed_label'))!='normal':continue
            key=row['metadata']['platform'],row['input']['method'],row['metadata']['operation_path']
            if key not in ops:return ['v7操作缺少文件填值規則']
            for spec in ops[key]:
                location,name=spec['location'],spec['name']
                if SENSITIVE.search(name):continue
                present,value=request_field(row['input'],location,name)
                if present:count+=len(violations(value,location,name,spec))
        if count:errors.append(f'{split}正常資料違反文件填值規則：{count}項')
    return errors
