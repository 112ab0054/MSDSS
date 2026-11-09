"""補真實促銷／目錄資料後驗證；履約與密碼Token只用本輪自己帳號／訂單。"""
import json
from pathlib import Path
import secrets
import uuid
from run_medusa_document_checks import TLSClient
from run_medusa_demo_flow import run as normal_flow
from medusa_native_fixture_runner import native_fixture

HERE = Path(__file__).resolve().parent


def main():
    config = json.loads((HERE / '.runtime/medusa-demo.json').read_text(encoding='utf-8-sig'))
    fixture = json.loads((HERE / 'reports/medusa-demo-v9-created-fixtures.json').read_text(encoding='utf-8'))
    c = TLSClient('https://127.0.0.1:18444', HERE / 'reports/medusa-demo-v9-fixture-checks.json',
                  config['publishable_api_key'], HERE / '.runtime/medusa-document-check-tls.crt')
    # 已有目錄資料後，完整正常流程會從清單動態取ID並驗明細。
    normal_flow(c)
    for key, path, singular in [('collection', '/store/collections', 'collection'), ('tag', '/store/product-tags', 'product_tag'),
                                ('type', '/store/product-types', 'product_type'), ('reason', '/store/return-reasons', 'return_reason')]:
        wanted = fixture[key]
        detail = c.request('GET', path + '/' + wanted['id'], template=path + '/{id}')
        actual = detail.get(singular, {})
        meaningful = 'title' if key == 'collection' else 'value'
        c.verify(actual.get('id') == wanted['id'] and actual.get(meaningful) == wanted[meaningful],
                 '讀回本輪建立的' + key + ' ID與實際內容，而非只檢查200', -1)
    region = next(r['response_body']['region'] for r in c.rows if r['operation_path'] == '/store/regions/{id}')
    product = next(r['response_body']['product'] for r in c.rows if r['operation_path'] == '/store/products/{id}')
    cart = c.request('POST', '/store/carts', {'region_id': region['id']})['cart']; cid = cart['id']
    cart = c.request('POST', f'/store/carts/{cid}/line-items', {'variant_id': product['variants'][0]['id'], 'quantity': 2}, '/store/carts/{id}/line-items')['cart']
    baseline = float(cart['total']); code = fixture['promotion']['code']
    applied = c.request('POST', f'/store/carts/{cid}/promotions', {'promo_codes': [code]}, '/store/carts/{id}/promotions')['cart']; apply_row = len(c.rows)-1
    reread = c.request('GET', f'/store/carts/{cid}', template='/store/carts/{id}')['cart']
    c.verify(any(p.get('code') == code for p in reread.get('promotions', [])) and float(reread['discount_total']) > 0
             and float(reread['total']) < baseline and float(applied['total']) == float(reread['total']),
             '真實10%促銷已套用：查回優惠碼、折扣大於0且總額下降', apply_row, -1)
    c.rows[apply_row]['promotion_effect_verified'] = True
    removed = c.request('DELETE', f'/store/carts/{cid}/promotions', {'promo_codes': [code]}, '/store/carts/{id}/promotions')['cart']; remove_row = len(c.rows)-1
    reread = c.request('GET', f'/store/carts/{cid}', template='/store/carts/{id}')['cart']
    c.verify(not any(p.get('code') == code for p in reread.get('promotions', [])) and float(reread['discount_total']) == 0
             and float(reread['total']) == baseline and float(removed['total']) == baseline,
             '移除同一個真實優惠碼後折扣歸0、總額恢復原值', remove_row, -1)
    c.rows[remove_row]['promotion_effect_verified'] = True
    # 原生workflow產生正確reset JWT，沒有手動簽發或公開JWT／密碼。
    owner_auth = c.headers.get('Authorization'); c.headers.pop('Authorization', None)
    email = 'reset-fixture-' + uuid.uuid4().hex + '@example.test'; password = secrets.token_urlsafe(24) + 'Aa1!'
    registration = c.request('POST', '/auth/customer/emailpass/register', {'email': email, 'password': password}, '/auth/customer/{auth_provider}/register')
    c.headers['Authorization'] = 'Bearer ' + registration['token']
    customer = c.request('POST', '/store/customers', {'email': email})['customer']
    native = native_fixture({'mode': 'reset', 'email': email})
    c.remember({'token': native['token']}); c.headers['Authorization'] = 'Bearer ' + native['token']
    new_password = secrets.token_urlsafe(24) + 'Bb2!'
    c.request('POST', '/auth/customer/emailpass/update', {'email': email, 'password': new_password}, '/auth/customer/{auth_provider}/update'); update_row = len(c.rows)-1
    c.headers.pop('Authorization', None)
    c.request('POST', '/auth/customer/emailpass', {'email': email, 'password': password}, '/auth/customer/{auth_provider}', allowed_status={401}); old_row = len(c.rows)-1
    login = c.request('POST', '/auth/customer/emailpass', {'email': email, 'password': new_password}, '/auth/customer/{auth_provider}'); new_row = len(c.rows)-1
    c.headers['Authorization'] = 'Bearer ' + login['token']
    me = c.request('GET', '/store/customers/me')['customer']
    c.verify(me['id'] == customer['id'], '原生reset token更新密碼：舊密碼401、新密碼登入並讀回同一顧客', update_row, old_row, new_row, -1)
    c.rows[update_row]['coverage_limitation'] = native['scope']
    c.headers['Authorization'] = owner_auth
    # 只履約本輪normal_flow新建的訂單，不碰其他使用者訂單。
    order = next(r['response_body']['order'] for r in c.rows if r['operation_path'] == '/store/orders/{id}')
    oid = order['id']; item = order['items'][0]
    fulfillment = native_fixture({'mode': 'fulfill', 'order_id': oid, 'item_id': item['id']})
    read = c.request('GET', f'/store/orders/{oid}', template='/store/orders/{id}')['order']
    actual_item = next(i for i in read['items'] if i['id'] == item['id'])
    c.verify(float(actual_item['detail']['fulfilled_quantity']) >= 1, '只對本輪測試訂單原生履約後，HTTP查回品項已履約數量至少1', -1)
    source_shipping = next(r['request_body']['option_id'] for r in c.rows if r['operation_path'] == '/store/carts/{id}/shipping-methods')
    returning = native_fixture({'mode': 'return_shipping', 'shipping_option_id': source_shipping, 'currency_code': region['currency_code']})
    options = c.request('GET', f'/store/shipping-options?cart_id={cid}&is_return=true', template='/store/shipping-options')['shipping_options']
    option = next(x for x in options if x['id'] == returning['shipping_option']['id'])
    c.verify(option['provider_id'] == 'manual_manual' and option['price_type'] == 'flat', '真實退貨配送選項可由Store API查到，使用離線manual固定費率', -1)
    returned = c.request('POST', '/store/returns', {'order_id': oid, 'items': [{'id': item['id'], 'quantity': 1, 'reason_id': fixture['reason']['id']}],
                    'return_shipping': {'option_id': option['id']}, 'note': 'MSDSS local demo only'})['return']; return_row = len(c.rows)-1
    check = c.request('GET', f'/store/orders/{oid}', template='/store/orders/{id}')['order']
    returned_item = next(i for i in check['items'] if i['id'] == item['id'])
    c.verify(returned.get('order_id') == oid and any(i.get('item_id') == item['id'] and float(i['quantity']) == 1 for i in returned.get('items', []))
             and float(returned_item['detail']['return_requested_quantity']) == 1,
             '真實退貨建立：訂單／品項／數量正確且查回退貨申請數量1', return_row, -1)
    c.evidence_metadata['native_fixture_scope'] = 'only own new test data; no SQL writes; no real payment/capture; no service config changes'
    c.save('passed')
    print(json.dumps({'requests': len(c.rows), 'assertions': len(c.checks), 'outcome': 'passed'}))


if __name__ == '__main__': main()
