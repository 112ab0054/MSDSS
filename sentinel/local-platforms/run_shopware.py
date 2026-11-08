"""Candidate real-platform flow. Untested until a completed evidence report exists."""
import argparse
import json
import secrets
import uuid
from pathlib import Path
from http_evidence import EvidenceClient

ROOT = Path(__file__).resolve().parent


def elements(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('elements'), list):
        raise RuntimeError('回應缺少 elements；須核對固定實例契約')
    return payload['elements']


def first(items, message):
    if not items:
        raise RuntimeError(message)
    return items[0]


def cart_item(cart, product_id):
    return first([x for x in cart.get('lineItems', []) if x.get('referencedId') == product_id], '購物車沒有目標商品')


def run(client, config):
    c = client
    context = c.request('GET', '/context')
    c.verify(bool(context.get('salesChannel', {}).get('id')) and bool(c.headers.get('sw-context-token')),
             '取得銷售通路與可延續的 context token', -1)
    gateway = c.request('GET', '/checkout/gateway', template='/checkout/gateway')
    c.verify(isinstance(gateway.get('payments'), list)
             and isinstance(gateway.get('shipments'), list)
             and isinstance(gateway.get('errors'), (list, dict)),
             '結帳 gateway 回傳付款、配送與錯誤集合', -1)
    # Supporting preparation endpoints are recorded, but do not count toward the selected 21 APIs.
    country = first(elements(c.request('POST', '/country', {'limit': 100,
        'filter': [{'type': 'equals', 'field': 'active', 'value': True}]})), '沒有可用國家')
    salutation = first(elements(c.request('POST', '/salutation', {'limit': 20})), '沒有稱謂設定')
    email = 'phase1-' + uuid.uuid4().hex + '@example.test'
    password = secrets.token_urlsafe(24) + 'aA1!'
    address = {'firstName': 'MSDSS', 'lastName': 'Test', 'street': 'Phase One Street 12',
               'zipcode': '10115', 'city': 'Berlin', 'countryId': country['id']}
    c.request('POST', '/account/register', {'salutationId': salutation['id'], 'firstName': 'MSDSS',
        'lastName': 'Test', 'email': email, 'password': password,
        'storefrontUrl': 'http://127.0.0.1:18082', 'acceptedDataProtection': True,
        'billingAddress': address})
    register_row = len(c.rows) - 1
    c.request('POST', '/account/login', {'username': email, 'password': password})
    login_row = len(c.rows) - 1
    customer = c.request('POST', '/account/customer', {})
    c.verify(customer.get('email') == email, '註冊後登入並讀回同一顧客', register_row, login_row, -1)
    products = elements(c.request('POST', '/product', {'limit': 50,
        'filter': [{'type': 'range', 'field': 'stock', 'parameters': {'gte': 3}}]}))
    product = first([p for p in products if p.get('available') and not p.get('childCount')], '缺少庫存至少 3 的可購買單品')
    c.verify(bool(product.get('id')), '商品列表含可購買商品', -1)
    pid = product['id']
    detail = c.request('POST', '/product/' + pid, {}, '/product/{productId}')
    c.verify(detail.get('product', {}).get('id') == pid, '商品詳情 ID 與列表一致', -1)
    search = c.request('POST', '/search', {'search': product.get('productNumber') or product['name'], 'limit': 50})
    c.verify(any(p.get('id') == pid for p in elements(search)), '搜尋可找到所選商品', -1)
    category_ids = product.get('categoryTree') or []
    if category_ids:
        listing = c.request('POST', '/product-listing/' + category_ids[-1], {'limit': 100}, '/product-listing/{categoryId}')
        c.verify(any(p.get('id') == pid for p in elements(listing)), '分類列表包含所選商品', -1)
    cart = c.request('GET', '/checkout/cart')
    c.verify(not cart.get('lineItems'), '新顧客初始購物車為空', -1)
    line_id = uuid.uuid4().hex
    c.request('POST', '/checkout/cart/line-item', {'items': [{'id': line_id, 'referencedId': pid,
        'type': 'product', 'quantity': 1, 'stackable': True, 'removable': True}]})
    add_row = len(c.rows) - 1
    cart = c.request('GET', '/checkout/cart')
    line_id = cart_item(cart, pid)['id']
    c.verify(cart_item(cart, pid).get('quantity') == 1, '加入商品後重新讀回數量 1', add_row, -1)
    c.request('PATCH', '/checkout/cart/line-item', {'items': [{'id': line_id, 'quantity': 2}]})
    update_row = len(c.rows) - 1
    cart = c.request('GET', '/checkout/cart')
    c.verify(cart_item(cart, pid).get('quantity') == 2, '修改後重新讀回數量 2', update_row, -1)
    c.request('POST', '/checkout/cart/line-item/delete', {'ids': [line_id]})
    remove_row = len(c.rows) - 1
    cart = c.request('GET', '/checkout/cart')
    c.verify(not cart.get('lineItems'), '移除後購物車沒有品項', remove_row, -1)
    c.request('POST', '/checkout/cart/line-item', {'items': [{'id': uuid.uuid4().hex,
        'referencedId': pid, 'type': 'product', 'quantity': 1}]})
    c.verify(cart_item(c.request('GET', '/checkout/cart'), pid).get('quantity') == 1, '重新加入結帳商品', -2, -1)
    saved = c.request('POST', '/account/address', {**address, 'salutationId': salutation['id']})
    address_row = len(c.rows) - 1
    aid = saved.get('id')
    addresses = elements(c.request('POST', '/account/list-address', {'limit': 100}))
    c.verify(bool(aid) and any(a.get('id') == aid and a.get('street') == address['street'] for a in addresses),
             '新增地址並由地址清單核對內容', address_row, -1)
    shipping = first(elements(c.request('GET', '/shipping-method?onlyAvailable=1', template='/shipping-method')),
                     '沒有可用配送方式')
    c.verify(bool(shipping.get('id')), '讀取可用配送方式', -1)
    methods = elements(c.request('GET', '/payment-method?onlyAvailable=1', template='/payment-method'))
    # Refuse external gateways. Never call /handle-payment or any remote payment URL.
    offline = [m for m in methods if m.get('id') in config['offline_payment_ids']]
    payment = first(offline, '未找到明確的原生 InvoicePayment／CashPayment；需要本機離線付款設定')
    c.verify(bool(payment.get('id')), '僅選用原生離線付款 handler', -1)
    c.request('PATCH', '/context', {'billingAddressId': aid, 'shippingAddressId': aid,
        'shippingMethodId': shipping['id'], 'paymentMethodId': payment['id']})
    save_row = len(c.rows) - 1
    context = c.request('GET', '/context')
    c.verify(context.get('shippingMethod', {}).get('id') == shipping['id']
             and context.get('paymentMethod', {}).get('id') == payment['id']
             and context.get('customer', {}).get('activeBillingAddress', {}).get('id') == aid
             and context.get('shippingLocation', {}).get('address', {}).get('id') == aid,
             '由 context 確認帳單／配送地址與配送／付款選項均已保存', save_row, -1)
    order = c.request('POST', '/checkout/order', {})
    create_row = len(c.rows) - 1
    oid = order.get('id')
    c.verify(bool(oid) and bool(order.get('orderNumber')), '建立訂單取得 ID 與訂單編號', create_row)
    result = c.request('POST', '/order', {'filter': [{'type': 'equals', 'field': 'id', 'value': oid}],
        'associations': {'lineItems': {}, 'addresses': {}, 'deliveries': {'associations': {'shippingMethod': {}}},
                         'transactions': {'associations': {'paymentMethod': {}}}, 'stateMachineState': {}}})
    confirmed = first(elements(result.get('orders', {})), '訂單清單沒有剛建立的訂單')
    c.verify(confirmed.get('id') == oid
        and any(i.get('referencedId') == pid and i.get('quantity') == 1 for i in confirmed.get('lineItems', []))
        and confirmed.get('stateMachineState', {}).get('technicalName') == 'open'
        and any(a.get('street') == address['street'] for a in confirmed.get('addresses', []))
        and any(d.get('shippingMethodId') == shipping['id'] for d in confirmed.get('deliveries', []))
        and any(t.get('paymentMethodId') == payment['id'] for t in confirmed.get('transactions', [])),
        '重新查單核對商品數量、地址、配送、離線付款與 open 訂單狀態', create_row, -1)
    c.request('POST', '/account/logout', {})
    logout_row = len(c.rows) - 1
    context = c.request('GET', '/context')
    c.verify(not context.get('customer'), '登出後 context 不再具有顧客身分', logout_row, -1)
    c.save('passed')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=ROOT / '.runtime/shopware.json')
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args()
    output = args.output or ROOT / 'reports' / ('shopware-' + uuid.uuid4().hex + '.json')
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    c = EvidenceClient('shopware', 'http://127.0.0.1:18082/store-api', output,
                       {'sw-access-key': config['access_key']})
    try:
        run(c, config)
    except (RuntimeError, KeyError, TypeError, ValueError) as error:
        # Exception messages are ours; never include raw credential/config content.
        c.save('failed', str(error) if isinstance(error, RuntimeError) else '回應結構不符；須核對實例契約')
        print('未通過；請查看已遮蔽紀錄：', output)
        return 1
    print('正常流程通過；證據：', output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
