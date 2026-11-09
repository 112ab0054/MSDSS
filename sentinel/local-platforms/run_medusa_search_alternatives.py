"""補查真實搜尋替代路由。新增候選路由不混入原79操作及其模型分數。"""
import json
from pathlib import Path
import urllib.parse
import uuid
from run_medusa_document_checks import TLSClient

HERE = Path(__file__).resolve().parent


def main():
    config = json.loads((HERE / '.runtime/medusa-demo.json').read_text(encoding='utf-8-sig'))
    c = TLSClient('https://127.0.0.1:18444', HERE / 'reports/medusa-demo-v9-search-alternatives.json',
                  config['publishable_api_key'], HERE / '.runtime/medusa-document-check-tls.crt')
    products = c.request('GET', '/store/products?limit=5', template='/store/products')['products']
    if not products: raise RuntimeError('缺真實商品，不能驗證搜尋')
    chosen = products[0]; query = urllib.parse.quote(chosen['title'], safe='')
    found = c.request('GET', '/store/products?q='+query, template='/store/products')['products']
    c.verify(any(x['id'] == chosen['id'] for x in found), '用回應取得的真實商品名稱搜尋，查回同一商品ID', -1)
    missing = 'msdss-no-product-' + uuid.uuid4().hex
    empty = c.request('GET', '/store/products?q='+missing, template='/store/products')['products']
    c.verify(empty == [], '不存在的隨機商品名稱查無資料，證實q並非被忽略', -1)
    c.request('GET', '/store/products/search?q='+query, template='/store/products/search', allowed_status={200,400,403,404,500})
    row = c.rows[-1]
    row['candidate_only'] = True
    row['model_scope_note'] = 'not in existing79 selected operations; no model score claimed for this candidate route'
    if row['status'] == 200:
        c.verify(any(x['id'] == chosen['id'] for x in row['response_body'].get('products', [])), '獨立搜尋路由能查回同一商品', -1)
    c.evidence_metadata['scope'] = 'supplementary compatibility probes; not added to original79 or aggregate model predictions'
    c.save('supplementary_route_check_complete')
    print(json.dumps({'requests': len(c.rows), 'list_q_verified': True, 'candidate_status': row['status'], 'candidate_response': row['response_body']},ensure_ascii=False))


if __name__ == '__main__': main()
