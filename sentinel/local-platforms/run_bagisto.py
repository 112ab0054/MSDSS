"""Real Bagisto API flow; a script existing does not mean it has passed."""
import argparse
import json
from pathlib import Path
import secrets
import uuid
from http_evidence import EvidenceClient

ROOT = Path(__file__).resolve().parent


def collection(value):
    if not isinstance(value, list):
        raise RuntimeError('預期 JSON 陣列；請核對固定實例輸出')
    return value


def choose(items, condition, message):
    for item in items:
        if condition(item):
            return item
    raise RuntimeError(message)


def run(c):
    products = collection(c.request('GET', '/products?query=MSDSS&per_page=50', template='/products'))
    product = choose(products, lambda p: p.get('sku') == 'MSDSS-PHASE1-SIMPLE', '測試商品種子不存在或尚未建立索引')
    c.verify(bool(product.get('id')), '列表找到本次正常流程專用商品', -1)
    pid = product['id']
    support = choose(products, lambda p: p.get('sku') == 'MSDSS-PHASE1-SUPPORT', '缺少供移除測試使用的第二個單品')
    support_id = support['id']
    detail = c.request('GET', '/products/' + str(pid), template='/products/{id}')
    c.verify(detail.get('id') == pid and detail.get('sku') == product['sku'], '讀回商品詳情核對 ID 與 SKU', -1)
    guest = c.request('POST', '/cart-tokens', {'createNew': True})
    c.verify(bool(guest.get('cartToken')) and not guest.get('items') and guest.get('customerId') is None,
             '建立空的獨立訪客購物車並取得 token', -1)
    email = 'phase1-' + uuid.uuid4().hex + '@example.test'
    password = secrets.token_urlsafe(24) + 'aA1!'
    c.request('POST', '/customers', {'firstName': 'MSDSS', 'lastName': 'Test', 'email': email,
        'password': password, 'confirmPassword': password})
    register = len(c.rows) - 1
    login = c.request('POST', '/customer/login', {'email': email, 'password': password})
    login_row = len(c.rows) - 1
    if not login.get('token'):
        raise RuntimeError('登入未取得 bearer token')
    c.headers['Authorization'] = 'Bearer ' + login['token']
    profile = collection(c.request('GET', '/customer-profile'))
    c.verify(any(p.get('email') == email for p in profile), '註冊登入後以 bearer 讀回同一會員', register, login_row, -1)
    c.request('POST', '/add-product-in-cart', {'productId': pid, 'quantity': 1})
    add = len(c.rows) - 1

    def cart():
        return c.request('POST', '/cart', {})

    def item(value):
        return choose(value.get('items') or [], lambda i: i.get('productId') == pid, '購物車未保存目標商品')

    current = cart()
    iid = item(current)['id']
    c.verify(item(current).get('quantity') == 1, '重新讀取購物車確認加購數量 1', add, -1)
    c.request('POST', '/add-product-in-cart', {'productId': support_id, 'quantity': 1})
    support_cart = cart()
    c.verify(any(i.get('productId') == support_id and i.get('quantity') == 1 for i in support_cart.get('items', [])),
             '加入第二個實體單品，供移除後保持可查詢的購物車', -2, -1)
    c.request('POST', '/update-cart-item', {'cartItemId': iid, 'quantity': 2})
    update = len(c.rows) - 1
    c.verify(item(cart()).get('quantity') == 2, '重新讀取確認修改數量 2', update, -1)
    c.request('POST', '/remove-cart-item', {'cartItemId': iid})
    remove = len(c.rows) - 1
    empty = cart()
    c.verify(len(empty.get('items', [])) == 1 and empty['items'][0].get('productId') == support_id
             and empty['items'][0].get('quantity') == 1,
             '重新讀取確認目標品項已移除，只保留第二個單品', remove, -1)
    c.request('POST', '/add-product-in-cart', {'productId': pid, 'quantity': 1})
    c.verify(item(cart()).get('quantity') == 1, '重新加入待結帳商品', -2, -1)
    address = {'firstName': 'MSDSS', 'lastName': 'Test', 'email': email, 'phone': '2025550100',
        'address1': 'Phase One Street 12', 'city': 'Los Angeles', 'state': 'CA',
        'postcode': '90001', 'country': 'US', 'defaultAddress': True}
    saved = c.request('POST', '/customer-addresses', address)
    create_address = len(c.rows) - 1
    aid = saved.get('id') or saved.get('addressId')
    addresses = collection(c.request('GET', '/customer-addresses'))
    c.verify(bool(aid) and any(str(a.get('id')) == str(aid) and a.get('city') == address['city'] for a in addresses),
             '由地址清單確認新增地址與城市', create_address, -1)
    c.request('PUT', '/customer-addresses/' + str(aid), {**address, 'city': 'San Francisco'}, '/customer-addresses/{id}')
    update_address = len(c.rows) - 1
    addresses = collection(c.request('GET', '/customer-addresses'))
    c.verify(any(str(a.get('id')) == str(aid) and a.get('city') == 'San Francisco' for a in addresses),
             '重新讀回確認地址更新', update_address, -1)
    checkout = c.request('POST', '/checkout-addresses', {
        'billingFirstName': 'MSDSS', 'billingLastName': 'Test', 'billingEmail': email,
        'billingAddress': address['address1'], 'billingCity': 'San Francisco', 'billingCountry': 'US',
        'billingState': 'CA', 'billingPostcode': '90001', 'billingPhoneNumber': address['phone'], 'useForShipping': True})
    address_row = len(c.rows) - 1
    c.verify(checkout.get('success') is True and checkout.get('billingCity') == 'San Francisco',
             '結帳地址保存回應與預期一致；訂單建立後再次核對', address_row)
    shipping = choose(collection(c.request('GET', '/checkout-shipping-methods')),
                      lambda m: bool(m.get('method')), '沒有可用配送方式')
    c.verify(bool(shipping['method']), '從實際回應取得配送代碼', -1)
    c.request('POST', '/checkout-shipping-methods', {'shippingMethod': shipping['method']})
    shipping_row = len(c.rows) - 1
    methods = collection(c.request('GET', '/payment-methods'))
    payment = choose(methods, lambda m: m.get('method') in ('cashondelivery', 'moneytransfer') and m.get('isAllowed'),
                     '沒有可用的本機離線付款方式')
    c.verify(bool(payment['method']), '只選用離線貨到付款或轉帳', -1)
    c.request('POST', '/checkout-payment-methods', {'paymentMethod': payment['method']})
    payment_row = len(c.rows) - 1
    created = c.request('POST', '/checkout-orders', {})
    create_order = len(c.rows) - 1
    oid = created.get('orderId')
    c.verify(bool(oid) and created.get('redirect') is False, '離線建單取得 orderId，沒有付款跳轉', create_order)
    orders = collection(c.request('GET', '/customer-orders'))
    c.verify(any(str(o.get('id')) == str(oid) for o in orders), '會員訂單清單包含剛建立的訂單', -1)
    order = c.request('GET', '/customer-orders/' + str(oid), template='/customer-orders/{id}')
    c.verify(str(order.get('id')) == str(oid) and order.get('status') == 'pending'
        and order.get('customerEmail') == email and order.get('shippingMethod') == shipping['method']
        and order.get('payment', {}).get('method') == payment['method']
        and any(i.get('productId') == pid and i.get('qtyOrdered') == 1 for i in order.get('items', []))
        and any(i.get('productId') == support_id and i.get('qtyOrdered') == 1 for i in order.get('items', []))
        and sum(i.get('qtyOrdered', 0) for i in order.get('items', [])) == 2
        and any(a.get('city') == 'San Francisco' and a.get('address') == address['address1']
                and a.get('addressType') == 'order_shipping' for a in order.get('addresses', []))
        and any(a.get('city') == 'San Francisco' and a.get('addressType') == 'order_billing' for a in order.get('addresses', [])),
        '訂單詳情核對商品數量、配送地址、配送付款與 pending 狀態', address_row, shipping_row, payment_row, create_order, -1)
    logout = c.request('POST', '/customer/logout', {})
    logout_row = len(c.rows) - 1
    c.request('GET', '/customer-profile', allowed_status={401, 403})
    c.verify(logout.get('success') is True and c.rows[-1]['status'] in (401, 403),
             '登出成功且原 bearer 無法再讀取顧客資料', logout_row, -1)
    c.save('passed')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=ROOT / '.runtime/bagisto.json')
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args()
    output = args.output or ROOT / 'reports' / ('bagisto-' + uuid.uuid4().hex + '.json')
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    c = EvidenceClient('bagisto', 'http://127.0.0.1:18081/api/shop', output,
        {'X-STOREFRONT-KEY': config['storefront_key'], 'X-Locale': config['locale'],
         'X-Channel': config['channel'], 'X-Currency': config['currency']})
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
