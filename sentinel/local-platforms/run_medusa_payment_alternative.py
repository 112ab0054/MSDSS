"""測目前版本付款session重建方式；只用本輪新cart與離線pp_system_default。"""
import json
from pathlib import Path
import uuid
from run_medusa_document_checks import TLSClient

HERE = Path(__file__).resolve().parent


def main():
    config = json.loads((HERE / '.runtime/medusa-demo.json').read_text(encoding='utf-8-sig'))
    c = TLSClient('https://127.0.0.1:18444', HERE / 'reports/medusa-demo-v9-payment-alternative.json',
                  config['publishable_api_key'], HERE / '.runtime/medusa-document-check-tls.crt')
    region = c.request('GET', '/store/regions')['regions'][0]
    products = c.request('GET', '/store/products?limit=5&region_id='+region['id'], template='/store/products')['products']
    product = next(p for p in products if p.get('variants'))
    cart = c.request('POST', '/store/carts', {'region_id': region['id']})['cart']; cid = cart['id']
    c.request('POST', f'/store/carts/{cid}/line-items', {'variant_id': product['variants'][0]['id'], 'quantity': 1}, '/store/carts/{id}/line-items')
    collection = c.request('POST', '/store/payment-collections', {'cart_id': cid})['payment_collection']; pcid = collection['id']
    marks = ['msdss-first-'+uuid.uuid4().hex, 'msdss-second-'+uuid.uuid4().hex]
    results = []
    for marker in marks:
        result = c.request('POST', f'/store/payment-collections/{pcid}/payment-sessions',
                           {'provider_id': 'pp_system_default', 'data': {'msdss_demo_marker': marker}},
                           '/store/payment-collections/{id}/payment-sessions')['payment_collection']
        sessions = result.get('payment_sessions', [])
        c.verify(result['id'] == pcid and len(sessions) == 1 and sessions[0]['provider_id'] == 'pp_system_default'
                 and sessions[0].get('data', {}).get('msdss_demo_marker') == marker,
                 '同一付款集合保留一個離線session且資料符合本次marker', -1)
        results.append(sessions[0])
    c.request('GET', f'/store/carts/{cid}', template='/store/carts/{id}'); cart_row = len(c.rows)-1
    linked = c.rows[cart_row]['response_body']['cart'].get('payment_collection', {})
    c.verify(linked.get('id') == pcid and linked.get('status') == 'not_paid'
             and linked.get('captured_amount') in (None, 0) and linked.get('authorized_amount') in (None, 0),
             '購物車連到同一付款集合且狀態not_paid；未授權／扣款金額為原生未初始化null或0', cart_row)
    summary = {'same_collection_id': pcid, 'session_ids': [s['id'] for s in results],
               'session_id_changed': results[0]['id'] != results[1]['id'], 'latest_marker_persisted': True,
               'payment_capture_performed': False,
               'scope': 'POST collection/payment-sessions creates or replaces session; not proof that absent POST session/{id} exists'}
    (HERE / 'reports/medusa-demo-v9-payment-alternative-proof.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    c.save('native_session_replacement_verified')
    print(json.dumps({'requests': len(c.rows), 'session_id_changed': summary['session_id_changed'], 'offline_only': True}))


if __name__ == '__main__': main()
