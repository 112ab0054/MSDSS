"""補測展示站79項範圍。未發行ID／未取得驗證碼的探查絕不列為正常成功。"""
import argparse
import http.cookies
import json
from pathlib import Path
import secrets
import urllib.request
import uuid
from http_evidence import EvidenceClient
from run_medusa_demo_flow import run as normal_flow
from run_medusa_mfa import totp

HERE = Path(__file__).resolve().parent
ALL_STATUS = set(range(200, 600))


class CookieMetadata(urllib.request.BaseHandler):
    def __init__(self, client): self.client = client
    def http_response(self, request, response):
        if self.client.rows and '/auth/session' in request.full_url:
            result = []
            for header in response.headers.get_all('Set-Cookie', []):
                cookies = http.cookies.SimpleCookie(); cookies.load(header)
                for name, value in cookies.items():
                    result.append({'name': name, 'secure': bool(value['secure']), 'domain': value['domain'],
                                   'path': value['path'], 'samesite': value['samesite']})
            self.client.rows[-1]['session_header_metadata_no_values'] = result
        return response


class Client(EvidenceClient):
    active_path = ''
    def remember(self, value):
        if self.active_path.startswith('/auth/') and isinstance(value, dict):
            if isinstance(value.get('code'), str): self.secrets.add(value['code'])
            if isinstance(value.get('recovery_codes'), list): self.secrets.update(str(x) for x in value['recovery_codes'])
        super().remember(value)
    def request(self, method, path, body=None, template=None, **kwargs):
        self.active_path = path
        try:
            return super().request(method, path, body, template, **kwargs)
        finally:
            if self.rows:
                row = self.rows[-1]
                print(f'{len(self.rows):03d} {method} {template or path.split("?")[0]} HTTP {row.get("status", "transport-error")}', flush=True)


def run(c):
    normal_flow(c)
    baseline_count = len(c.rows)
    order = next(r['response_body']['order'] for r in reversed(c.rows) if r['operation_path'] == '/store/orders/{id}' and r['status'] == 200)
    owner_token = c.headers['Authorization']; oid = order['id']
    owner_id = next(r['response_body']['customer']['id'] for r in c.rows if r['operation_path'] == '/store/customers' and r['status'] == 200)
    registration = next(r for r in c.rows if r['operation_path'] == '/auth/customer/{auth_provider}/register')
    email = registration['request_body']['email']; password = registration['request_body']['password']
    state = {'order': order, 'owner_token': owner_token, 'email': email, 'password': password}
    failures = []

    def call(method, path, body=None, template=None, reason=None, probe=False):
        value = c.request(method, path, body, template, allowed_status=ALL_STATUS)
        row = c.rows[-1]; row['supplemental_test'] = True
        if reason: row['precondition_limitation'] = reason
        if probe: row['route_probe_only'] = True
        return value

    def case(name, fn):
        start = len(c.rows)
        try: fn()
        except (RuntimeError, KeyError, TypeError, ValueError, StopIteration) as error:
            failures.append({'case': name, 'error_type': type(error).__name__})
            if len(c.rows) > start: c.rows[-1]['test_case_limitation'] = name + '未完成；依實際回應另查前置條件'
        c.save('supplemental_running')

    def check(condition, description, *indexes): c.verify(condition, description, *(indexes or (-1,)))

    def mfa():
        data = call('GET', '/auth/mfa/factors')
        if c.rows[-1]['status'] != 200: return
        check(isinstance(data.get('mfa_factors'), list), '取得目前測試帳號的真實MFA因子清單')
        data = call('POST', '/auth/mfa/factors', {'provider': 'totp', 'label': 'MSDSS remaining API test', 'issuer': 'MSDSS'})
        enrollment = len(c.rows) - 1
        if c.rows[-1]['status'] != 200:
            c.rows[-1]['precondition_limitation'] = 'MFA註冊失敗：' + str(data.get('message', '未取得註冊秘密'))[:350]
            return
        factor = data['mfa_factor']; secret = data['secret']; state['factor_id'] = factor['id']
        check(bool(secret) and factor.get('status') != 'enabled', '取得真實待啟用MFA因子與秘密；公開紀錄遮蔽', enrollment)
        code = totp(secret); c.remember({'token': code})
        data = call('POST', '/auth/mfa/factors/' + factor['id'] + '/verify', {'code': code}, '/auth/mfa/factors/{id}/verify')
        if c.rows[-1]['status'] != 200: return
        check(data['mfa_factor']['status'] == 'enabled', '真實TOTP啟用成功')
        login = call('POST', '/auth/customer/emailpass', {'email': email, 'password': password}, '/auth/customer/{auth_provider}')
        if login.get('token'): c.headers['Authorization'] = 'Bearer ' + login['token']
        challenge = login.get('mfa_challenge') or login.get('challenge')
        if isinstance(challenge, dict) and challenge.get('id'):
            state['challenge_id'] = challenge['id']
            # 避免沿用註冊同一時窗的TOTP；不捏造驗證碼。
            import time
            time.sleep(31 - int(time.time()) % 30)
            code = totp(secret); c.remember({'token': code})
            verified = call('POST', '/auth/mfa/challenges/' + challenge['id'] + '/verify', {'method': 'totp', 'code': code}, '/auth/mfa/challenges/{id}/verify')
            if verified.get('token'):
                c.headers['Authorization'] = 'Bearer ' + verified['token']; check(True, '登入挑戰取得真實驗證後token')
        recovery = call('POST', '/auth/mfa/recovery-codes', {'count': 3})
        if c.rows[-1]['status'] == 200 and isinstance(recovery.get('recovery_codes'), list):
            codes = recovery['recovery_codes']; check(len(codes) == 3 and len(set(codes)) == 3, '真實產生三組不同備援碼')
            call('DELETE', '/auth/mfa/factors/' + factor['id'], {'method': 'recovery-code', 'code': codes[0]}, '/auth/mfa/factors/{id}')
            disable = len(c.rows) - 1
            factors = call('GET', '/auth/mfa/factors')['mfa_factors']
            check(not any(x['id'] == factor['id'] and x['status'] == 'enabled' for x in factors), '使用真實備援碼停用因子並重新查證', disable, -1)
        c.headers['Authorization'] = owner_token
    case('MFA lifecycle', mfa)

    def auth_extras():
        c.headers['Authorization'] = owner_token
        call('POST', '/auth/customer/emailpass/verification/confirm', {}, '/auth/customer/emailpass/verification/confirm',
             '固定清單的舊驗證路徑；核對路由存在性，不使用假驗證碼', True)
        call('POST', '/auth/customer/emailpass/callback', {}, '/auth/customer/{auth_provider}/callback',
             '目前只配置emailpass，沒有第三方OAuth提供者／授權回呼資料', True)
        call('POST', '/auth/customer/emailpass/reset-password', {'identifier': email}, '/auth/customer/{auth_provider}/reset-password',
             '對自己的測試帳號申請重設；201只表示受理，尚未取得通知送達的重設token')
        verification = call('POST', '/auth/verification/request', {'entity_id': email, 'entity_type': 'email', 'code_provider': 'token'})
        if c.rows[-1]['status'] == 201:
            obj = verification.get('verification', {})
            check(obj.get('entity_id') == email and obj.get('code_provider') == 'token', '對真實測試email建立驗證請求，回應身分與提供者一致')
            state['verification_code'] = verification.get('code') or obj.get('code')
        else: c.rows[-1]['precondition_limitation'] = '未取得可供確認的驗證請求；回應錯誤另記'
        code = state.get('verification_code')
        if code:
            c.remember({'token': code})
            confirmed = call('POST', '/auth/verification/confirm', {'code': code, 'code_provider': 'token'})
            check(confirmed.get('entity_id') == email and bool(confirmed.get('verified_at')), '使用實際取得的驗證碼確認同一email')
        else:
            call('POST', '/auth/verification/confirm', {'code_provider': 'token'}, reason='未配置驗證通知取碼途徑，沒有真實code；本次僅驗證缺參數會被拒絕', probe=True)
        new_password = secrets.token_urlsafe(24) + 'Aa1!'
        call('POST', '/auth/customer/emailpass/update', {'password': new_password}, '/auth/customer/{auth_provider}/update')
        if c.rows[-1]['status'] == 200:
            update = len(c.rows) - 1
            login = call('POST', '/auth/customer/emailpass', {'email': email, 'password': new_password}, '/auth/customer/{auth_provider}')
            check(bool(login.get('token')), '自己的測試密碼更新後，新密碼能重新登入', update, -1)
            if login.get('token'): c.headers['Authorization'] = 'Bearer ' + login['token']; state['owner_token'] = c.headers['Authorization']
        else: c.rows[-1]['precondition_limitation'] = '登入JWT不等於reset-password郵件token；缺少合法重設token，未捏造或自行簽發'
    case('auth extras', auth_extras)
    c.headers['Authorization'] = state['owner_token']

    def cart_extras():
        region = call('GET', '/store/regions')['regions'][0]
        product = next(x for x in call('GET', '/store/products?limit=20&region_id=' + region['id'], template='/store/products')['products'] if x.get('variants'))
        address = {'first_name': 'MSDSS', 'last_name': 'Remaining', 'address_1': '12 Test Street', 'city': 'London', 'country_code': 'gb', 'postal_code': 'SW1A 1AA'}
        cart = call('POST', '/store/carts', {'region_id': region['id'], 'shipping_address': address, 'items': [{'variant_id': product['variants'][0]['id'], 'quantity': 1}]})['cart']
        cid = cart['id']; state['cart_id'] = cid
        taxes = call('POST', f'/store/carts/{cid}/taxes', {}, '/store/carts/{id}/taxes')
        if c.rows[-1]['status'] == 200:
            check(taxes['cart']['id'] == cid and bool(taxes['cart']['items']) and all(isinstance(x.get('tax_lines'), list) for x in taxes['cart']['items']), '真實購物車重新計稅，ID、品項及tax_lines一致')
        added = call('POST', f'/store/carts/{cid}/promotions', {'promo_codes': []}, '/store/carts/{id}/promotions')
        if c.rows[-1]['status'] == 200:
            check(added['cart']['id'] == cid and not added['cart'].get('promotions'), 'POST促銷以空陣列清除設定並確認空清單；未聲稱有效折扣套用成功')
            c.rows[-1]['coverage_limitation'] = '只驗證清除促銷的合法分支；沒有有效折扣代碼，未驗證有折扣分支'
        removed = call('DELETE', f'/store/carts/{cid}/promotions', {'promo_codes': []}, '/store/carts/{id}/promotions')
        if c.rows[-1]['status'] == 200:
            check(removed['cart']['id'] == cid and not removed['cart'].get('promotions'), 'DELETE促銷空陣列後仍無折扣；未聲稱移除已套用折扣')
            c.rows[-1]['coverage_limitation'] = '沒有已套用折扣可移除，只驗證合法空陣列分支'
        options = call('GET', '/store/shipping-options?cart_id=' + cid, template='/store/shipping-options')['shipping_options']
        if options:
            option = options[0]; state['shipping_option_id'] = option['id']
            calc = call('POST', '/store/shipping-options/' + option['id'] + '/calculate', {'cart_id': cid}, '/store/shipping-options/{id}/calculate')
            if c.rows[-1]['status'] == 200:
                got = calc['shipping_option']; check(got['id'] == option['id'] and isinstance(got.get('amount'), (int, float)), '真實配送選項計價回傳同一ID及數值價格')
            else: c.rows[-1]['precondition_limitation'] = '目前manual固定費率提供者的額外calculate實際失敗，根因未定位；固定費率結帳前輪已成功'
        # 這些功能在2.21.0沒有原生route；真實車ID，缺未發行code時明確省略。
        for method, suffix, body in [('POST', 'gift-cards', {}), ('DELETE', 'gift-cards', {}), ('POST', 'store-credits', {'amount': 1})]:
            call(method, f'/store/carts/{cid}/{suffix}', body, '/store/carts/{id}/' + suffix,
                 '版本／功能路由探查；沒有發行禮卡或儲值金，不能列為正常成功', True)
        call('POST', '/store/search', {'entity': 'product', 'filters': {'q': product['title']}, 'pagination': {'take': 20}},
             reason='核對目前展示站是否提供search；不使用其他平台或假索引回應', probe=True)
    case('cart extras', cart_extras)

    def catalog_details():
        for plural, singular in [('collections', 'collection'), ('product-tags', 'product_tag'), ('product-types', 'product_type'), ('return-reasons', 'return_reason')]:
            result = call('GET', '/store/' + plural); values = result[plural.replace('-', '_')]
            if values:
                detail = call('GET', '/store/' + plural + '/' + values[0]['id'], template='/store/' + plural + '/{id}')
                check(detail[singular]['id'] == values[0]['id'], '以實際清單ID讀回' + singular)
            else:
                call('GET', '/store/' + plural + '/msdss-probe-no-issued-id', template='/store/' + plural + '/{id}',
                     reason='資料庫清單為空，沒有真實明細ID；此未發行識別值只做404負向路由探查，不能當正常流程', probe=True)
        call('GET', '/store/store-credit-accounts', reason='核對儲值帳戶功能；清單若未提供不視為成功', probe=True)
        call('POST', '/store/store-credit-accounts/claim', {}, reason='沒有已發行claim code，僅路由／必填驗證探查，不捏造code', probe=True)
        call('GET', '/store/store-credit-accounts/msdss-probe-no-issued-account', template='/store/store-credit-accounts/{id}', reason='未發行帳戶ID，只做路由探查', probe=True)
        call('GET', '/store/gift-cards/msdss-probe-no-issued-card', template='/store/gift-cards/{idOrCode}', reason='未發行禮卡ID或code，只做路由探查', probe=True)
    case('catalog details', catalog_details)

    def transfers():
        email2 = 'transfer-' + uuid.uuid4().hex + '@example.test'; password2 = secrets.token_urlsafe(24) + 'Aa1!'
        c.headers.pop('Authorization', None)
        auth = call('POST', '/auth/customer/emailpass/register', {'email': email2, 'password': password2}, '/auth/customer/{auth_provider}/register')
        c.headers['Authorization'] = 'Bearer ' + auth['token']
        receiver = call('POST', '/store/customers', {'email': email2})['customer']
        login = call('POST', '/auth/customer/emailpass', {'email': email2, 'password': password2}, '/auth/customer/{auth_provider}')
        c.headers['Authorization'] = 'Bearer ' + login['token']
        receiver_token = c.headers['Authorization']
        def ownership_check(description):
            c.headers['Authorization'] = state['owner_token']
            owner_orders = call('GET', '/store/orders')['orders']; owner_row = len(c.rows) - 1
            c.headers['Authorization'] = receiver_token
            receiver_orders = call('GET', '/store/orders')['orders']
            check(any(x['id'] == oid for x in owner_orders) and not any(x['id'] == oid for x in receiver_orders), description, owner_row, -1)
        requested = call('POST', f'/store/orders/{oid}/transfer/request', {'description': 'MSDSS own test order transfer'}, '/store/orders/{id}/transfer/request')
        if c.rows[-1]['status'] == 200:
            obj = requested['order']; check(obj['id'] == oid and owner_id != receiver['id'], '自己的兩個測試帳號申請移轉，回傳同一訂單')
            c.rows[-1]['coverage_limitation'] = '只驗證申請受理與owner不變，接受移轉仍需合法通知token'
            ownership_check('申請移轉後兩個帳號的訂單清單證明owner未變；不依賴回應未提供的customer_id')
        else: c.rows[-1]['precondition_limitation'] = '移轉申請未建立；依實際錯誤另記'
        cancelled = call('POST', f'/store/orders/{oid}/transfer/cancel', {}, '/store/orders/{id}/transfer/cancel')
        if c.rows[-1]['status'] == 200:
            check(cancelled['order']['id'] == oid, '取消自己的移轉請求回傳同一訂單')
            ownership_check('取消移轉後兩個帳號的訂單清單證明owner仍未變')
        else: c.rows[-1]['precondition_limitation'] = '目前身分或移轉狀態不允許取消；回應保留'
        for action in ('accept', 'decline'):
            call('POST', f'/store/orders/{oid}/transfer/{action}', {}, '/store/orders/{id}/transfer/' + action,
                 '沒有送達的合法transfer token；只測缺少token會被拒絕，不自行簽發或偽造', True)
        c.headers['Authorization'] = state['owner_token']
    case('transfers', transfers)

    def returns():
        c.headers['Authorization'] = state['owner_token']
        options = call('GET', '/store/shipping-options?cart_id=' + state['cart_id'] + '&is_return=true', template='/store/shipping-options').get('shipping_options', [])
        shipping = options[0]['id'] if options else state.get('shipping_option_id')
        if not shipping: return
        result = call('POST', '/store/returns', {'order_id': oid, 'items': [{'id': order['items'][0]['id'], 'quantity': 1}], 'return_shipping': {'option_id': shipping}, 'note': 'MSDSS own unfulfilled test order return precondition'})
        if c.rows[-1]['status'] == 200:
            check(result.get('return', {}).get('order_id') == oid, '以真實測試訂單與品項建立退貨')
        else: c.rows[-1]['precondition_limitation'] = '本次測試訂單尚未履約／缺退貨配送條件，回應為前置拒絕；未修改後台履約或假裝退貨成功'
    case('returns', returns)

    # 缺真實MFA因子／挑戰時，負向探查仍明確保留「不可驗成功」原因。
    for method, path, template, body in [
        ('POST', '/auth/mfa/challenges/msdss-probe-no-challenge/verify', '/auth/mfa/challenges/{id}/verify', {'method': 'totp'}),
        ('POST', '/auth/mfa/factors/msdss-probe-no-factor/verify', '/auth/mfa/factors/{id}/verify', {}),
        ('DELETE', '/auth/mfa/factors/msdss-probe-no-factor', '/auth/mfa/factors/{id}', {}),
        ('POST', '/auth/mfa/recovery-codes', '/auth/mfa/recovery-codes', {'count': 3})]:
        if not any(r['method'] == method and r['operation_path'] == template for r in c.rows):
            call(method, path, body, template, 'MFA未完成註冊，沒有真實因子／挑戰／備援碼前置；只做路由與缺參數探查', True)
    # 若某case中途失敗，不能把剩餘項目默默當已測。
    c.save('coverage_complete_with_limitations')
    print(json.dumps({'requests': len(c.rows), 'baseline_requests': baseline_count, 'case_failures': failures}, ensure_ascii=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url', default='http://127.0.0.1:18085')
    p.add_argument('--config', type=Path, default=HERE / '.runtime/medusa-demo.json')
    p.add_argument('--output', type=Path, default=HERE / 'reports/medusa-demo-v9-remaining.json')
    args = p.parse_args(); cfg = json.loads(args.config.read_text(encoding='utf-8-sig'))
    c = Client('medusa', args.base_url, args.output, {'x-publishable-api-key': cfg['publishable_api_key']})
    c.opener.add_handler(CookieMetadata(c))
    run(c)


if __name__ == '__main__': main()
