"""Real Sylius Standard flow. Optional verification mail is deliberately not invoked."""
import argparse
import json
from pathlib import Path
import secrets
import urllib.parse
import uuid
from http_evidence import EvidenceClient

ROOT = Path(__file__).resolve().parent
BASE = '/api/v2/shop'


def collection(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ('hydra:member', 'member'):
            if isinstance(value.get(key), list):
                return value[key]
    raise RuntimeError('缺少 JSON-LD collection member；須核對實例契約')


def choose(items, condition, message):
    for item in items:
        if condition(item):
            return item
    raise RuntimeError(message)


def iri(value):
    if isinstance(value, str) and value.startswith(BASE + '/'):
        return value
    if isinstance(value, dict) and isinstance(value.get('@id'), str) and value['@id'].startswith(BASE + '/'):
        return value['@id']
    raise RuntimeError('回應缺少本機 Shop API IRI')


def same_resource(value, target):
    if isinstance(value, dict):
        return bool(value.get('@id') and value.get('@id') == target.get('@id')) or bool(value.get('code') and value.get('code') == target.get('code'))
    return value == target.get('@id')


def run(c, config):
    products = collection(c.request('GET', BASE + '/products?itemsPerPage=30', template=BASE + '/products'))
    product = choose(products, lambda p: bool(p.get('code')) and bool(p.get('variants')), '沒有可購買的商品與 variant')
    c.verify(bool(product['code']), '商品列表含可選商品與 variant', -1)
    code = urllib.parse.quote(product['code'], safe='')
    detail = c.request('GET', BASE + '/products/' + code, template=BASE + '/products/{code}')
    c.verify(detail.get('code') == product['code'], '商品詳情與列表代碼一致', -1)
    if detail.get('slug'):
        by_slug = c.request('GET', BASE + '/products-by-slug/' + urllib.parse.quote(detail['slug'], safe=''),
                            template=BASE + '/products-by-slug/{slug}', allowed_status={200, 301})
        slug_row = len(c.rows) - 1
        if c.rows[-1]['status'] == 301:
            target = urllib.parse.urlsplit(c.rows[-1]['response_headers'].get('Location', ''))
            if target.netloc or not target.path.startswith(BASE + '/products/') or target.query or target.fragment:
                raise RuntimeError('slug 回應不是預期的本機商品 canonical redirect；停止追蹤')
            by_slug = c.request('GET', target.path, template=BASE + '/products/{code}')
        c.verify(by_slug.get('code') == product['code'], '由 slug 及本機 canonical 商品路徑查詢到同一商品', slug_row, -1)
    variant = iri(detail['variants'][0])
    email = 'phase1-' + uuid.uuid4().hex + '@example.test'
    password = secrets.token_urlsafe(24) + 'aA1!'
    c.request('POST', BASE + '/customers', {'firstName': 'MSDSS', 'lastName': 'Test', 'email': email, 'password': password})
    register = len(c.rows) - 1
    login = c.request('POST', BASE + '/customers/token', {'email': email, 'password': password})
    login_row = len(c.rows) - 1
    if not login.get('token'):
        raise RuntimeError('登入沒有取得 JWT')
    c.headers['Authorization'] = 'Bearer ' + login['token']
    address = {'firstName': 'MSDSS', 'lastName': 'Test', 'countryCode': config['country'],
               'street': 'Phase One Street 12', 'city': 'New York', 'postcode': '10001'}
    saved = c.request('POST', BASE + '/addresses', address)
    create_address = len(c.rows) - 1
    address_uri = iri(saved)
    confirmed = c.request('GET', address_uri, template=BASE + '/addresses/{id}')
    c.verify(confirmed.get('street') == address['street'] and confirmed.get('city') == address['city'],
             '帶 JWT 新增地址後重新讀回核對內容', register, login_row, create_address, -1)
    addresses = collection(c.request('GET', BASE + '/addresses'))
    c.verify(any(a.get('@id') == address_uri for a in addresses), '顧客地址清單含新增地址', -1)
    order = c.request('POST', BASE + '/orders', {})
    token = order.get('tokenValue')
    if not token:
        raise RuntimeError('建車回應缺少 tokenValue')
    order_uri = BASE + '/orders/' + urllib.parse.quote(token, safe='')
    c.verify(order.get('state') == 'cart' and not order.get('items'), '建立空的 cart 並取得動態 tokenValue', -1)

    def read_order():
        return c.request('GET', order_uri, template=BASE + '/orders/{tokenValue}')

    def current_item(value):
        return choose(value.get('items', []), lambda i: same_resource(i.get('variant'), {'@id': variant}),
                      '購物車未保存選用 variant')

    c.request('POST', order_uri + '/items', {'productVariant': variant, 'quantity': 1}, BASE + '/orders/{tokenValue}/items')
    add = len(c.rows) - 1
    current = read_order()
    item = current_item(current)
    item_uri = iri(item)
    c.verify(item.get('quantity') == 1, '重新讀取確認加購數量 1', add, -1)
    items = collection(c.request('GET', order_uri + '/items', template=BASE + '/orders/{tokenValue}/items'))
    c.verify(any(i.get('@id') == item_uri and i.get('quantity') == 1 for i in items), '購物車品項清單一致', -1)
    c.request('PATCH', item_uri, {'quantity': 2}, BASE + '/orders/{tokenValue}/items/{orderItemId}',
              'application/merge-patch+json')
    update = len(c.rows) - 1
    c.verify(current_item(read_order()).get('quantity') == 2, '重新讀取確認數量改為 2', update, -1)
    c.request('DELETE', item_uri, template=BASE + '/orders/{tokenValue}/items/{orderItemId}')
    remove = len(c.rows) - 1
    c.verify(not read_order().get('items'), '重新讀取確認移除後購物車為空', remove, -1)
    c.request('POST', order_uri + '/items', {'productVariant': variant, 'quantity': 1}, BASE + '/orders/{tokenValue}/items')
    c.verify(current_item(read_order()).get('quantity') == 1, '重新加入結帳商品', -2, -1)
    c.request('PUT', order_uri, {'email': email, 'billingAddress': address, 'shippingAddress': address}, BASE + '/orders/{tokenValue}')
    address_row = len(c.rows) - 1
    current = read_order()
    c.verify(current.get('customer', {}).get('email') == email and current.get('shippingAddress', {}).get('street') == address['street']
             and current.get('billingAddress', {}).get('street') == address['street'],
             '重新讀取確認訂單 email 與帳單／配送地址', address_row, -1)
    shipment = choose(current.get('shipments', []), lambda s: bool(s.get('@id')), '購物車尚無 shipment')
    shipment_uri = iri(shipment)
    shipping = choose(collection(c.request('GET', shipment_uri + '/methods',
        template=BASE + '/orders/{tokenValue}/shipments/{shipmentId}/methods')), lambda m: bool(m.get('@id')), '沒有可用配送方式')
    c.verify(bool(shipping.get('code')), '從該 shipment 可用方式取得配送 IRI 與 code', -1)
    c.request('PATCH', shipment_uri, {'shippingMethod': iri(shipping)},
              BASE + '/orders/{tokenValue}/shipments/{shipmentId}', 'application/merge-patch+json')
    shipping_row = len(c.rows) - 1
    methods = collection(c.request('GET', BASE + '/payment-methods'))
    c.verify(any(m.get('code') in config['offline_payment_codes'] for m in methods), '付款列表含資料庫核對為 offline 的方式', -1)
    current = read_order()
    payment = choose(current.get('payments', []), lambda p: bool(p.get('@id')), '購物車尚無 payment')
    payment_uri = iri(payment)
    method = choose(collection(c.request('GET', payment_uri + '/methods',
        template=BASE + '/orders/{tokenValue}/payments/{paymentId}/methods')),
        lambda m: m.get('code') in config['offline_payment_codes'], '該 payment 沒有可用的 offline 方式')
    c.verify(bool(method.get('@id')), '只選用可用且已核對為 offline 的付款 IRI', -1)
    c.request('PATCH', payment_uri, {'paymentMethod': iri(method)},
              BASE + '/orders/{tokenValue}/payments/{paymentId}', 'application/merge-patch+json')
    payment_row = len(c.rows) - 1
    current = read_order()
    c.verify(any(same_resource(s.get('method'), shipping) for s in current.get('shipments', []))
             and any(same_resource(p.get('method'), method) for p in current.get('payments', [])),
             '重新讀取確認配送與離線付款方式已保存', shipping_row, payment_row, -1)
    c.request('PATCH', order_uri + '/complete', {}, BASE + '/orders/{tokenValue}/complete', 'application/merge-patch+json')
    complete = len(c.rows) - 1
    current = read_order()
    c.verify(current.get('state') == 'new' and current.get('checkoutState') == 'completed'
             and bool(current.get('number')) and current_item(current).get('quantity') == 1
             and current.get('shippingAddress', {}).get('street') == address['street']
             and any(same_resource(s.get('method'), shipping) for s in current.get('shipments', []))
             and any(same_resource(p.get('method'), method) for p in current.get('payments', [])),
             '重新查單確認 new／completed、訂單編號、數量、地址與配送付款選項', complete, -1)
    orders = collection(c.request('GET', BASE + '/orders'))
    c.verify(any(o.get('tokenValue') == token for o in orders), '登入會員訂單清單包含新訂單', -1)
    c.save('passed')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=ROOT / '.runtime/sylius.json')
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args()
    output = args.output or ROOT / 'reports' / ('sylius-' + uuid.uuid4().hex + '.json')
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    c = EvidenceClient('sylius', 'http://127.0.0.1:18083', output, {'Accept': 'application/ld+json'})
    try:
        run(c, config)
    except (RuntimeError, KeyError, TypeError, ValueError) as error:
        c.save('failed', str(error) if isinstance(error, RuntimeError) else '回應結構不符；須核對實例契約')
        print('未通過；請查看已遮蔽紀錄：', output)
        return 1
    print('正常流程通過；證據：', output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
