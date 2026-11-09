"""自己的測試訂單：唯讀取平台原生產生的token，測accept／decline。未驗證郵件送達。"""
import json
from pathlib import Path
import re
import secrets
import subprocess
import uuid
from run_medusa_document_checks import TLSClient
from run_medusa_demo_flow import run as normal_flow

HERE = Path(__file__).resolve().parent


def db_query(sql):
    result = subprocess.run(['docker', 'exec', '-i', 'mirage-commerce-real-db-1', 'sh', '-c',
                             'exec psql -X -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -A'],
                            input='BEGIN READ ONLY; ' + sql + '; ROLLBACK;', capture_output=True, text=True, timeout=15)
    if result.returncode: raise RuntimeError('自己的測試訂單唯讀查詢失敗；錯誤不公開')
    return json.loads(result.stdout)


def native_token(order_id, receiver_id):
    if not all(re.fullmatch(r'[A-Za-z0-9_]+', x) for x in (order_id, receiver_id)): raise ValueError('不合法測試ID')
    rows = db_query("SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT c.id AS change_id,a.details->>'token' AS native_token FROM order_change c JOIN order_change_action a ON a.order_change_id=c.id WHERE c.order_id='" + order_id + "' AND c.change_type='transfer' AND c.status='requested' AND c.deleted_at IS NULL AND a.reference_id='" + receiver_id + "' AND a.deleted_at IS NULL AND a.details->>'token' IS NOT NULL) t")
    if len(rows) != 1 or not rows[0]['native_token']: raise RuntimeError('未找到唯一的本輪平台原生token，不生成替代值')
    return rows[0]


def main():
    config = json.loads((HERE / '.runtime/medusa-demo.json').read_text(encoding='utf-8-sig'))
    c = TLSClient('https://127.0.0.1:18443', HERE / 'reports/medusa-demo-v9-native-token-transfers.json',
                  config['publishable_api_key'], HERE / '.runtime/medusa-document-check-tls.crt')
    normal_flow(c)
    order = next(r['response_body']['order'] for r in c.rows if r['operation_path'] == '/store/orders/{id}' and r['status'] == 200)
    oid = order['id']; owner_token = c.headers['Authorization']; proofs = []
    email = 'native-transfer-' + uuid.uuid4().hex + '@example.test'; password = secrets.token_urlsafe(24) + 'Aa1!'
    c.headers.pop('Authorization', None)
    auth = c.request('POST', '/auth/customer/emailpass/register', {'email': email, 'password': password}, '/auth/customer/{auth_provider}/register')
    c.headers['Authorization'] = 'Bearer ' + auth['token']
    receiver = c.request('POST', '/store/customers', {'email': email})['customer']
    auth = c.request('POST', '/auth/customer/emailpass', {'email': email, 'password': password}, '/auth/customer/{auth_provider}')
    receiver_token = 'Bearer ' + auth['token']
    for action in ('decline', 'accept'):
        c.headers['Authorization'] = receiver_token
        c.request('POST', f'/store/orders/{oid}/transfer/request', {'description': 'MSDSS native-issued token integration test'}, '/store/orders/{id}/transfer/request')
        token_data = native_token(oid, receiver['id']); c.remember({'token': token_data['native_token']})
        c.headers['Authorization'] = owner_token
        response = c.request('POST', f'/store/orders/{oid}/transfer/{action}', {'token': token_data['native_token']}, '/store/orders/{id}/transfer/' + action)
        action_row = len(c.rows) - 1
        c.rows[action_row]['coverage_limitation'] = '平台於本輪真實transfer request產生的token，從自己訂單的資料列唯讀取得；沒有自行簽發，郵件／通知送達未驗證'
        c.verify(response['order']['id'] == oid, '使用平台實際產生token呼叫' + action + '並回傳同一訂單', action_row)
        owner_orders = c.request('GET', '/store/orders')['orders']; owner_row = len(c.rows) - 1
        c.headers['Authorization'] = receiver_token
        receiver_orders = c.request('GET', '/store/orders')['orders']; receiver_row = len(c.rows) - 1
        if action == 'decline':
            c.verify(any(x['id'] == oid for x in owner_orders) and not any(x['id'] == oid for x in receiver_orders), '拒絕移轉後，原owner仍有訂單、接收者沒有', action_row, owner_row, receiver_row)
        else:
            c.verify(not any(x['id'] == oid for x in owner_orders) and any(x['id'] == oid for x in receiver_orders), '接受移轉後，訂單已從原owner清單移到接收者清單', action_row, owner_row, receiver_row)
        state = db_query("SELECT json_build_object('id',id,'status',status,'deleted_at',deleted_at) FROM order_change WHERE id='" + token_data['change_id'] + "'")
        proofs.append({'action': action, 'order_id': oid, 'receiver_id': receiver['id'], 'state': state,
                       'read_only': True, 'native_issued_value_used': True, 'notification_delivery_verified': False})
        if action == 'decline': c.verify(state['status'] == 'declined', '唯讀查回平台移轉變更狀態declined', action_row)
        else: c.verify(state['status'] == 'confirmed', '唯讀查回平台移轉變更狀態confirmed', action_row)
    (HERE / 'reports/medusa-demo-v9-native-token-provenance.json').write_text(json.dumps({'scope': 'only own newly-created test order; SELECT only; native tokens never published', 'proofs': proofs}, ensure_ascii=False, indent=2), encoding='utf-8')
    c.save('passed_with_unverified_notification_delivery')
    print(json.dumps({'requests': len(c.rows), 'decline_and_accept_real_native_tokens': True, 'notification_delivery_verified': False}))


if __name__ == '__main__': main()
