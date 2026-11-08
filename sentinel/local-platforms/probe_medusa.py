"""Real local route/feature probes, kept separate from completed checkout evidence."""
import json
from pathlib import Path
import uuid
from http_evidence import EvidenceClient

HERE = Path(__file__).resolve().parent


def main():
    config = json.loads((HERE / '.runtime/medusa.json').read_text(encoding='utf-8-sig'))
    c = EvidenceClient('medusa', 'http://127.0.0.1:18084',
        HERE / 'reports' / ('medusa-probes-' + uuid.uuid4().hex + '.json'),
        {'x-publishable-api-key': config['publishable_api_key']})
    try:
        regions = c.request('GET', '/store/regions')['regions']
        region = next(r for r in regions if any(x['iso_2'] == 'gb' for x in r['countries']))
        product = c.request('GET', '/store/products?region_id=' + region['id'], template='/store/products')['products'][0]
        address = {'first_name': 'MSDSS', 'last_name': 'Probe', 'address_1': '12 Test Street',
                   'city': 'London', 'country_code': 'gb', 'postal_code': 'SW1A 1AA'}
        cart = c.request('POST', '/store/carts', {'region_id': region['id'], 'shipping_address': address,
            'items': [{'variant_id': product['variants'][0]['id'], 'quantity': 1}]})['cart']
        cid = cart['id']
        probes = [
            ('POST', '/auth/customer/emailpass/verification/confirm', {}, '/auth/customer/emailpass/verification/confirm'),
            ('POST', f'/store/carts/{cid}/gift-cards', {}, '/store/carts/{id}/gift-cards'),
            ('DELETE', f'/store/carts/{cid}/gift-cards', {}, '/store/carts/{id}/gift-cards'),
            ('POST', f'/store/carts/{cid}/store-credits', {}, '/store/carts/{id}/store-credits'),
            ('GET', '/store/gift-cards/MSDSS-ROUTE-PROBE-NO-ISSUED-CARD', None, '/store/gift-cards/{idOrCode}'),
            ('GET', '/store/store-credit-accounts', None, '/store/store-credit-accounts'),
            ('POST', '/store/store-credit-accounts/claim', {}, '/store/store-credit-accounts/claim'),
            ('GET', '/store/store-credit-accounts/MSDSS-ROUTE-PROBE-NO-ACCOUNT', None, '/store/store-credit-accounts/{id}'),
        ]
        for method, path, body, template in probes:
            c.request(method, path, body, template, allowed_status={200, 400, 401, 403, 404, 405, 422})
            c.rows[-1]['route_probe_only'] = True
            c.rows[-1]['probe_limitation'] = '僅核對實機路由，未發行禮卡／儲值帳戶；404 不算正常業務成功，須同時核對原生 route 原始碼。'
        taxes = c.request('POST', f'/store/carts/{cid}/taxes', {}, '/store/carts/{id}/taxes')
        c.verify(taxes['cart']['id'] == cid and bool(taxes['cart']['items'])
            and all(isinstance(i.get('tax_lines'), list) for i in taxes['cart']['items']),
            '原生稅額重算回傳同一購物車、真實品項及稅額明細', -1)
        shipping = c.request('GET', '/store/shipping-options?cart_id=' + cid, template='/store/shipping-options')['shipping_options'][0]
        calculated = c.request('POST', '/store/shipping-options/' + shipping['id'] + '/calculate',
            {'cart_id': cid}, '/store/shipping-options/{id}/calculate', allowed_status={200, 400, 422, 500})
        if c.rows[-1]['status'] == 200:
            calculated = calculated['shipping_option']
            c.verify(calculated['id'] == shipping['id'] and isinstance(calculated.get('amount'), (int, float))
                and calculated['amount'] == shipping['amount'], '同一購物車的固定配送費率計算與可用配送清單金額一致', -1)
        else:
            c.rows[-1]['precondition_limitation'] = '原生 manual 固定費率配送可結帳，但額外 calculate 操作實機回 500；尚未釐清提供者是否支援，保留問題，不視為成功。'
        result = c.request('POST', '/store/search', {'entity': 'product', 'filters': {'q': product['title']},
            'pagination': {'take': 20}})
        c.verify(any(hit.get('id') == product['id'] and hit.get('document', {}).get('title') == product['title']
            for group in result['results'] for hit in group['hits']), '原生搜尋索引命中剛由商品 API 取得的同一商品 ID 與標題', -1)
        c.save('passed')
        print('探查完成；證據：', c.output)
        return 0
    except (RuntimeError, KeyError, TypeError, ValueError, StopIteration):
        c.save('failed', '額外實機探查未通過，請查看遮蔽證據；不影響另外保存的完整購物流程結果。')
        print('探查未通過；證據：', c.output)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
