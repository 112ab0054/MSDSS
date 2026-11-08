"""Isolated Medusa 2.22.4 normal API validation; never used to train or tune the model."""
import argparse
import json
from pathlib import Path
import secrets
import urllib.parse
import uuid
from http_evidence import EvidenceClient

ROOT = Path(__file__).resolve().parent


def choose(items, condition, message):
    for item in items:
        if condition(item):
            return item
    raise RuntimeError(message)


def rows(payload, key):
    if not isinstance(payload, dict) or not isinstance(payload.get(key), list):
        raise RuntimeError('回應缺少預期清單：' + key)
    return payload[key]


def run(c):
    providers = rows(c.request('GET', '/auth/customer/providers'), 'providers')
    provider = choose(providers, lambda p: p.get('id') == 'emailpass', '未配置 emailpass 認證提供者')
    c.verify(provider.get('flow') == 'credentials', '實際列出 emailpass 認證方式', -1)
    region = choose(rows(c.request('GET', '/store/regions'), 'regions'),
        lambda r: any(x.get('iso_2') == 'gb' for x in r.get('countries', [])), '缺少供本次正常購物使用的 GB region')
    rid = region['id']
    c.verify(bool(rid) and bool(region.get('currency_code')), '取得真實商務區域與幣別', -1)
    rr = c.request('GET', '/store/regions/' + rid, template='/store/regions/{id}')
    c.verify(rr['region']['id'] == rid, '區域明細 ID 與清單一致', -1)
    currencies = rows(c.request('GET', '/store/currencies?limit=20', template='/store/currencies'), 'currencies')
    c.verify(bool(currencies), '取得平台幣別清單', -1)
    currency = c.request('GET', '/store/currencies/' + region['currency_code'], template='/store/currencies/{code}')
    c.verify(currency['currency']['code'] == region['currency_code'], '讀取選用區域的實際幣別明細', -1)
    locales = rows(c.request('GET', '/store/locales'), 'locales')
    c.verify(isinstance(locales, list), 'Translation 路由回傳 locales 清單；空清單代表尚未配置語系', -1)
    # Real, fixture-backed catalog list/detail checks. IDs always come from responses.
    catalogs = [('/store/collections', 'collections', 'collection'),
                ('/store/product-categories', 'product_categories', 'product_category'),
                ('/store/product-options', 'product_options', 'product_option'),
                ('/store/product-tags', 'product_tags', 'product_tag'),
                ('/store/product-types', 'product_types', 'product_type'),
                ('/store/return-reasons', 'return_reasons', 'return_reason')]
    for path, plural, singular in catalogs:
        values = rows(c.request('GET', path + '?limit=20', template=path), plural)
        c.verify(isinstance(values, list), '取得 ' + plural + ' 清單', -1)
        if values:
            value = values[0]
            detail = c.request('GET', path + '/' + value['id'], template=path + '/{id}')
            c.verify(detail[singular]['id'] == value['id'], '由回應 ID 讀回 ' + singular + ' 明細', -1)
    products = rows(c.request('GET', '/store/products?limit=10&region_id=' + rid, template='/store/products'), 'products')
    product = choose(products, lambda p: bool(p.get('variants')), '沒有可購買變體的商品')
    pid = product['id']
    variant = product['variants'][0]
    vid = variant['id']
    c.verify(bool(pid) and bool(vid), '商品清單回傳可選商品與真實 variant ID', -1)
    detail = c.request('GET', '/store/products/' + pid + '?region_id=' + rid, template='/store/products/{id}')
    c.verify(detail['product']['id'] == pid and any(v['id'] == vid for v in detail['product']['variants']),
             '商品詳情與所選變體一致', -1)
    variants = rows(c.request('GET', '/store/product-variants?id=' + vid + '&region_id=' + rid,
        template='/store/product-variants'), 'variants')
    c.verify(any(v['id'] == vid for v in variants), '變體清單可查回所選 variant', -1)
    email = 'phase1-' + uuid.uuid4().hex + '@example.test'
    password = secrets.token_urlsafe(24) + 'aA1!'
    auth = c.request('POST', '/auth/customer/emailpass/register', {'email': email, 'password': password},
                     '/auth/customer/{auth_provider}/register')
    register_auth = len(c.rows) - 1
    if not auth.get('token'):
        raise RuntimeError('註冊認證未取得 JWT；可能需要另外的郵件驗證前置流程')
    c.headers['Authorization'] = 'Bearer ' + auth['token']
    customer = c.request('POST', '/store/customers', {'email': email, 'first_name': 'MSDSS', 'last_name': 'Test'})['customer']
    customer_row = len(c.rows) - 1
    auth = c.request('POST', '/auth/customer/emailpass', {'email': email, 'password': password}, '/auth/customer/{auth_provider}')
    login_row = len(c.rows) - 1
    c.headers['Authorization'] = 'Bearer ' + auth['token']
    me = c.request('GET', '/store/customers/me')['customer']
    c.verify(me['id'] == customer['id'] and me['email'] == email,
             '認證註冊、建立顧客、登入後讀回同一顧客', register_auth, customer_row, login_row, -1)
    refreshed = c.request('POST', '/auth/token/refresh')
    refresh_row = len(c.rows) - 1
    if not refreshed.get('token'):
        raise RuntimeError('token refresh 沒有回傳新 JWT')
    c.headers['Authorization'] = 'Bearer ' + refreshed['token']
    c.verify(c.request('GET', '/store/customers/me')['customer']['id'] == customer['id'],
             '更新後 JWT 仍可讀回同一顧客', refresh_row, -1)
    bearer = c.headers['Authorization']
    c.request('POST', '/auth/session')
    session_row = len(c.rows) - 1
    c.headers.pop('Authorization')
    c.verify(bool(list(c.cookie_jar)) and c.request('GET', '/store/customers/me')['customer']['id'] == customer['id'],
             '移除 Bearer 後，僅靠真實 Cookie session 維持登入', session_row, -1)
    c.request('DELETE', '/auth/session')
    logout_row = len(c.rows) - 1
    c.request('GET', '/store/customers/me', allowed_status={401, 403})
    c.verify(c.rows[-1]['status'] in (401, 403), '結束 Cookie session 後不再具有顧客身分', logout_row, -1)
    c.headers['Authorization'] = bearer
    c.request('POST', '/store/customers/me', {'first_name': 'MSDSS Verified', 'phone': '2025550100'})
    update_customer = len(c.rows) - 1
    me = c.request('GET', '/store/customers/me')['customer']
    c.verify(me['first_name'] == 'MSDSS Verified' and me['phone'] == '2025550100', '顧客更新後重新查詢確認', update_customer, -1)
    address = {'first_name': 'MSDSS', 'last_name': 'Test', 'address_1': '12 Test Street',
        'city': 'London', 'country_code': 'gb', 'postal_code': 'SW1A 1AA', 'phone': '2025550100'}
    created_address = c.request('POST', '/store/customers/me/addresses', {**address, 'address_name': 'MSDSS local test'})
    address_row = len(c.rows) - 1
    address_list = created_address['customer']['addresses']
    saved = choose(address_list, lambda a: a.get('address_1') == address['address_1'], '新增地址未出現在顧客資料')
    aid = saved['id']
    detail = c.request('GET', '/store/customers/me/addresses/' + aid, template='/store/customers/me/addresses/{address_id}')
    c.verify(detail['address']['id'] == aid and detail['address']['city'] == 'London', '以動態地址 ID 重新讀回內容', address_row, -1)
    c.request('POST', '/store/customers/me/addresses/' + aid, {'city': 'Oxford', 'postal_code': 'OX1 1AA'},
              '/store/customers/me/addresses/{address_id}')
    update_address = len(c.rows) - 1
    addresses = rows(c.request('GET', '/store/customers/me/addresses'), 'addresses')
    c.verify(any(a['id'] == aid and a['city'] == 'Oxford' for a in addresses), '更新地址後清單反映新內容', update_address, -1)
    # Create a real guest cart with minimal address objects and initial line item.
    # No address id/timestamps or items[].id are supplied: this checks the questionable old documentation.
    c.headers.pop('Authorization')
    cart = c.request('POST', '/store/carts', {'region_id': rid, 'shipping_address': address,
        'billing_address': address, 'items': [{'variant_id': vid, 'quantity': 1}]})['cart']
    cid = cart['id']
    cart_row = len(c.rows) - 1
    c.verify(bool(cid) and cart.get('customer_id') is None and bool(cart['shipping_address']['id'])
        and any(i['variant_id'] == vid and i['quantity'] == 1 for i in cart['items']),
        '最小地址與初始品項即可真實建車；地址 ID 由伺服器產生', cart_row)
    c.headers['Authorization'] = bearer
    c.request('POST', '/store/carts/' + cid + '/customer', {}, '/store/carts/{id}/customer')
    transfer_row = len(c.rows) - 1

    def read_cart():
        return c.request('GET', '/store/carts/' + cid, template='/store/carts/{id}')['cart']

    def item(value):
        return choose(value.get('items', []), lambda x: x.get('variant_id') == vid, '購物車沒有目標變體')

    c.verify(read_cart().get('customer_id') == customer['id'], '把訪客購物車移交給目前登入顧客並重新查證', transfer_row, -1)
    c.request('POST', '/store/carts/' + cid, {'email': email, 'shipping_address': address, 'billing_address': address}, '/store/carts/{id}')
    update_cart = len(c.rows) - 1
    cart = read_cart()
    c.verify(cart['email'] == email and cart['shipping_address']['address_1'] == address['address_1'], '重新讀回 email 與購物車地址', update_cart, -1)
    c.request('POST', '/store/carts/' + cid + '/line-items', {'variant_id': vid, 'quantity': 1}, '/store/carts/{id}/line-items')
    add = len(c.rows) - 1
    cart = read_cart()
    iid = item(cart)['id']
    c.verify(item(cart)['quantity'] == 2, '再次加入同一變體後，購物車合併為數量 2', add, -1)
    c.request('POST', '/store/carts/' + cid + '/line-items/' + iid, {'quantity': 3}, '/store/carts/{id}/line-items/{line_id}')
    update_item = len(c.rows) - 1
    c.verify(item(read_cart())['quantity'] == 3, '修改品項後讀回數量 3', update_item, -1)
    c.request('DELETE', '/store/carts/' + cid + '/line-items/' + iid, template='/store/carts/{id}/line-items/{line_id}')
    remove = len(c.rows) - 1
    c.verify(not read_cart()['items'], '刪除最後品項後，真實購物車為空且仍可查詢', remove, -1)
    c.request('POST', '/store/carts/' + cid + '/line-items', {'variant_id': vid, 'quantity': 1}, '/store/carts/{id}/line-items')
    c.verify(item(read_cart())['quantity'] == 1, '重新加入結帳用商品', -2, -1)
    shipping = choose(rows(c.request('GET', '/store/shipping-options?cart_id=' + cid,
        template='/store/shipping-options'), 'shipping_options'), lambda s: s.get('provider_id') == 'manual_manual', '沒有本機 manual 配送選項')
    c.verify(bool(shipping['id']), '取得真實可用的本機配送選項', -1)
    c.request('POST', '/store/carts/' + cid + '/shipping-methods', {'option_id': shipping['id']}, '/store/carts/{id}/shipping-methods')
    shipping_row = len(c.rows) - 1
    payment = choose(rows(c.request('GET', '/store/payment-providers?region_id=' + rid,
        template='/store/payment-providers'), 'payment_providers'), lambda p: p['id'] == 'pp_system_default', '沒有原生離線 system 付款提供者')
    c.verify(payment['id'] == 'pp_system_default', '只選擇原生離線付款提供者', -1)
    pc = c.request('POST', '/store/payment-collections', {'cart_id': cid})['payment_collection']
    pcid = pc['id']
    c.verify(bool(pcid), '為真實購物車建立付款集合', -1)
    pc = c.request('POST', '/store/payment-collections/' + pcid + '/payment-sessions',
        {'provider_id': payment['id']}, '/store/payment-collections/{id}/payment-sessions')['payment_collection']
    session = choose(pc['payment_sessions'], lambda s: s['provider_id'] == payment['id'], '沒有建立離線付款 session')
    c.verify(bool(session['id']), '付款集合含實際建立的離線 session', -1)
    c.request('POST', '/store/payment-collections/' + pcid + '/payment-sessions/' + session['id'],
        {'client_data': {'msdss_phase1_note': 'normal-checkout'}}, '/store/payment-collections/{id}/payment-sessions/{session_id}')
    payment_update = len(c.rows) - 1
    cart = read_cart()
    c.verify(any(s.get('shipping_option_id') == shipping['id'] for s in cart.get('shipping_methods', [])),
             '重新讀回已保存的配送方式', shipping_row, -1)
    completed = c.request('POST', '/store/carts/' + cid + '/complete', {}, '/store/carts/{id}/complete')
    complete = len(c.rows) - 1
    if completed.get('type') != 'order' or not completed.get('order', {}).get('id'):
        raise RuntimeError('結帳沒有實際建立訂單，即使 HTTP 200 也不算通過')
    oid = completed['order']['id']
    order = c.request('GET', '/store/orders/' + oid, template='/store/orders/{id}')['order']
    c.verify(order['id'] == oid and order.get('status') == 'pending' and order.get('email') == email
        and any(i.get('variant_id') == vid and i.get('quantity') == 1 for i in order.get('items', []))
        and order.get('shipping_address', {}).get('address_1') == address['address_1']
        and any(s.get('shipping_option_id') == shipping['id'] for s in order.get('shipping_methods', []))
        and order.get('payment_status') == 'authorized'
        and any(p['id'] == pcid and p.get('status') == 'authorized' and p.get('captured_amount') == 0
                for p in order.get('payment_collections', [])),
        '建單後重新讀回 pending 訂單、商品數量、地址與配送選項', complete, -1)
    orders = rows(c.request('GET', '/store/orders'), 'orders')
    c.verify(any(o['id'] == oid for o in orders), '登入顧客的訂單清單包含剛建立的訂單', -1)
    c.request('DELETE', '/store/customers/me/addresses/' + aid, template='/store/customers/me/addresses/{address_id}')
    delete_address = len(c.rows) - 1
    c.verify(not any(a['id'] == aid for a in rows(c.request('GET', '/store/customers/me/addresses'), 'addresses')),
             '刪除測試顧客地址後重新查詢確認', delete_address, -1)
    # Payment update persistence is verified separately using its returned collection.
    updated = c.rows[payment_update]['response_body']['payment_collection']
    updated_session = choose(updated.get('payment_sessions', []), lambda s: s['id'] == session['id'],
                             '付款 session 更新後回應缺少原 session')
    if updated_session.get('client_data', {}).get('msdss_phase1_note') == 'normal-checkout':
        c.verify(True, '付款 session client_data 更新可由實際回應核對', payment_update)
    else:
        c.rows[payment_update]['precondition_limitation'] = (
            '原生 pp_system_default 接受 client_data 但不回傳／保存此提供者特定資料；'
            '只確認路由受理與 session 身分一致，不能宣稱已驗證 PSP 客戶端資料變更。')
    c.save('passed')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=ROOT / '.runtime/medusa.json')
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args()
    output = args.output or ROOT / 'reports' / ('medusa-' + uuid.uuid4().hex + '.json')
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    c = EvidenceClient('medusa', 'http://127.0.0.1:18084', output, {'x-publishable-api-key': config['publishable_api_key']})
    try:
        run(c)
    except (RuntimeError, KeyError, TypeError, ValueError) as error:
        c.save('failed', str(error) if isinstance(error, RuntimeError) else '回應結構不符；須核對實例契約')
        print('未通過；請查看已遮蔽紀錄：', output)
        return 1
    print('正常流程通過；證據：', output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
