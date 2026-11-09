"""閘道整合測試：使用模擬上游，不冒充 Medusa 實機或模型準確率證據。"""
import asyncio
from contextlib import asynccontextmanager
import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import threading
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

import httpx

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('tested_gateway', Path(__file__).with_name('app.py'))
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


class Predictor:
    """只驗證資料流，固定回傳攻擊，不把假模型當成訓練成果。"""
    mode, exploratory = 'offline', True

    def __init__(self):
        self.samples, self.checked = [], False

    def self_test(self):
        self.checked = True

    def predict(self, sample):
        self.samples.append(sample)
        return {'label': 'xss', 'mode': self.mode, 'exploratory': self.exploratory}


def reply(status=200, content=b'ok', headers=None):
    return httpx.Response(status, headers=headers, stream=httpx.ByteStream(content))


@asynccontextmanager
async def running(handler, predictor=None, **environment):
    settings = {'MEDUSA_UPSTREAM': 'http://backend.test', 'GATEWAY_MODEL_DIR': 'fixture' if predictor else '',
                'GATEWAY_ANALYSIS_TIMEOUT': '1', **environment}
    with patch.dict(os.environ, settings), patch.dict(sys.modules, {'predict': SimpleNamespace(Predictor=lambda _: predictor)}):
        async with gateway.app.router.lifespan_context(gateway.app):
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as upstream:
                gateway.app.state.client = upstream
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway.app), base_url='http://gateway.test') as client:
                    yield client


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    async def test_generated_request_ids_match_logs_upstream_and_response(self):
        """自動編號逐筆不同，且推論、後端與回應三者能對應；不加入模型特徵。"""
        observed, model = [], Predictor()
        def backend(request):
            observed.append(request)
            return reply(headers={'X-Request-ID': 'upstream-other-id'})
        with self.assertLogs(gateway.log, level='INFO') as logs:
            async with running(backend, model) as client:
                responses = [await client.get('/store/products') for _ in range(2)]
        ids = [r.headers['x-request-id'] for r in responses]
        self.assertNotEqual(*ids)
        for identifier, wire in zip(ids, observed):
            self.assertEqual(str(uuid.UUID(identifier)), identifier)
            self.assertEqual(wire.headers.get_list('x-request-id'), [identifier])
            self.assertIn('request_id=' + identifier, str(logs.output))
        self.assertEqual(model.samples[0], model.samples[1])
        self.assertNotIn('x-request-id', model.samples[0]['headers'])

    async def test_request_id_preserved_or_replaced_including_unselected_api(self):
        """合法值沿用；非法及重複值重建；清單外 API 也能追蹤但不推論。"""
        observed = []
        def backend(request):
            observed.append(request)
            return reply()
        valid = '11111111-1111-4111-8111-111111111111'
        async with running(backend) as client:
            for headers in ({'X-Request-ID': valid}, {'X-Request-ID': 'bad-value'},
                            [('X-Request-ID', valid), ('X-Request-ID', valid)]):
                response = await client.get('/not-selected', headers=headers)
                identifier = response.headers['x-request-id']
                uuid.UUID(identifier)
                self.assertEqual(observed[-1].headers.get_list('x-request-id'), [identifier])
                if headers == {'X-Request-ID': valid}:
                    self.assertEqual(identifier, valid)
                else:
                    self.assertNotEqual(identifier, valid)

    async def test_upstream_errors_include_request_id(self):
        """連線失敗／逾時仍回傳同一編號，方便查詢失敗請求。"""
        for error, status in ((httpx.ConnectError, 502), (httpx.ReadTimeout, 504)):
            def backend(request):
                raise error('test upstream error', request=request)
            async with running(backend) as client:
                response = await client.get('/store/products')
                self.assertEqual(response.status_code, status)
                uuid.UUID(response.headers['x-request-id'])

    async def test_real_local_http_transport_preserves_target_and_cookie_isolation(self):
        """真正經過本機 TCP／HTTPX 傳輸，避免只靠 MockTransport 判斷原文保留。"""
        observed, payload = [], gzip.compress(b'local transport passed')
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                observed.append((self.path, self.headers.get('Cookie')))
                self.send_response(200)
                self.send_header('Content-Encoding', 'gzip')
                self.send_header('Content-Length', str(len(payload)))
                self.send_header('Set-Cookie', 'a=1; Path=/')
                self.send_header('Set-Cookie', 'b=2; Path=/')
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            settings = {'MEDUSA_UPSTREAM': f'http://127.0.0.1:{server.server_port}', 'GATEWAY_MODEL_DIR': ''}
            with patch.dict(os.environ, settings):
                async with gateway.app.router.lifespan_context(gateway.app):
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway.app), base_url='http://gateway.test') as client:
                        request = httpx.Request('GET', 'http://gateway.test')
                        request.url = gateway.ForwardURL(httpx.URL('http://gateway.test'), b'/store/products/%66ixture?q=A%2fb&q=x')
                        response = await client.send(request)
                        client.cookies.clear()
                        await client.get('/store/products')
            self.assertEqual(observed, [('/store/products/%66ixture?q=A%2fb&q=x', None), ('/store/products', None)])
            self.assertEqual(response.content, b'local transport passed')
            self.assertEqual(len(response.headers.get_list('set-cookie')), 2)
        finally:
            await asyncio.to_thread(server.shutdown)
            server.server_close()
            thread.join()

    async def test_model_copy_redacted_original_request_preserved(self):
        observed, model = [], Predictor()
        def backend(request):
            observed.append(request)
            return reply(422)
        raw = b' { "name":"O\'Brien", "password":"private-password" } '
        with self.assertLogs(gateway.log, level='INFO') as logs:
            async with running(backend, model) as client:
                response = await client.post('/store/carts/%63art?q=A%2fb&q=A+B&token=private-token',
                    content=raw, headers=[('Content-Type', 'application/json'), ('Authorization', 'Bearer private-auth'),
                                          ('Cookie', 'sid=private-cookie'), ('X-Extra', 'a'), ('X-Extra', 'b')])
        self.assertEqual(response.status_code, 422)  # 預測攻擊仍轉送，後端錯誤也照實回傳。
        wire, sample = observed[0], model.samples[0]
        self.assertEqual(wire.url.raw_path, b'/store/carts/%63art?q=A%2fb&q=A+B&token=private-token')
        self.assertEqual(wire.content, raw)
        self.assertEqual(wire.headers['authorization'], 'Bearer private-auth')
        self.assertEqual(wire.headers['cookie'], 'sid=private-cookie')
        self.assertEqual(wire.headers.get_list('x-extra'), ['a', 'b'])
        self.assertEqual(sample['raw_query'], 'q=A%2fb&q=A+B&token=[REDACTED]')
        self.assertEqual(sample['raw_body'], raw.decode().replace('private-password', '[REDACTED]'))
        self.assertEqual(sample['headers']['authorization'], '[REDACTED]')
        self.assertTrue(model.checked)
        self.assertNotIn('private-', json.dumps(sample) + str(logs.output))

    async def test_cookies_isolated_and_compressed_redirect_preserved(self):
        cookies = []
        payload = gzip.compress(b'compressed response')
        def backend(request):
            cookies.append(request.headers.get('cookie'))
            return reply(302, payload, [('Content-Encoding', 'gzip'), ('Location', '/login'),
                ('Set-Cookie', 'a=1; Path=/'), ('Set-Cookie', 'b=2; Path=/'), ('Connection', 'X-Hop'), ('X-Hop', 'remove')])
        async with running(backend) as client:
            first = await client.get('/store/customers/me')
            client.cookies.clear()  # 第二個訪客，不繼承上一位瀏覽器的 Cookie。
            await client.get('/store/customers/me', headers={'Cookie': 'own=visitor2'})
            client.cookies.clear()
            await client.get('/store/customers/me')
        self.assertEqual(cookies, [None, 'own=visitor2', None])
        self.assertEqual(first.status_code, 302)
        self.assertEqual(first.content, b'compressed response')
        self.assertEqual(first.headers.get_list('set-cookie'), ['a=1; Path=/', 'b=2; Path=/'])
        self.assertEqual(first.headers['location'], '/login')
        self.assertNotIn('x-hop', first.headers)

    async def test_all_79_analyzed_other_routes_only_forwarded(self):
        operations = json.loads((ROOT / 'sentinel/analysis/api-extension/medusa-holdout-inventory.json').read_text())['operations']
        observed = []
        def backend(request):
            observed.append((request.method, request.url.path))
            return reply(404)
        model = Predictor()
        async with running(backend, model) as client:
            for operation in operations:
                path = re.sub(r'\{[^}]+\}', 'fixture', operation['path'])
                response = await client.request(operation['method'], path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(observed[-1], (operation['method'], path))
            self.assertEqual((await client.get('/unknown-path')).status_code, 404)
        self.assertEqual(len(operations), 79)
        self.assertEqual(len(observed), 80)
        self.assertEqual(len(model.samples), 79)

    async def test_unselected_methods_paths_only_forwarded_without_analysis(self):
        observed, model = [], Predictor()
        def backend(request):
            observed.append(request)
            return reply()
        cases = [('GET', '/unknown-path'), ('GET', '/_gateway/health'), ('GET', '/admin/users'),
                 ('POST', '/store/products'), ('DELETE', '/store/products/id'),
                 ('HEAD', '/store/products'), ('OPTIONS', '/store/products'),
                 ('GET', '/store/products/id/extra'), ('GET', '/store/products/'),
                 ('GET', '/store/products/id/%2F'), ('GET', '/store/products/id/%2e%2e'),
                 ('GET', '/store/products/../orders')]
        async with running(backend, model) as client:
            for method, path in cases:
                outgoing = httpx.Request(method, 'http://gateway.test')
                outgoing.url = gateway.ForwardURL(httpx.URL('http://gateway.test'), path.encode())
                self.assertEqual((await client.send(outgoing)).status_code, 200, (method, path))
        self.assertEqual(len(observed), len(cases))
        self.assertFalse(model.samples)  # 非偵測目標只轉送，不呼叫模型，也不額外拒絕。

    async def test_encoded_attack_ids_still_enter_selected_detection(self):
        model = Predictor()
        async with running(lambda r: reply(), model) as client:
            for identifier in ['%2F', '%2e%2e', '%3Cscript%3Ealert(1)%3C%2Fscript%3E']:
                self.assertEqual((await client.get('/store/products/' + identifier)).status_code, 200)
        self.assertEqual(len(model.samples), 3)  # 編碼值仍是 {id}，不因解碼出斜線就跳過模型。

    async def test_slow_prediction_does_not_queue_other_requests(self):
        entered, release = threading.Event(), threading.Event()
        model = Predictor()
        original = model.predict
        def slow(sample):
            entered.set()
            release.wait(3)
            return original(sample)
        model.predict = slow
        async with running(lambda r: reply(), model, GATEWAY_ANALYSIS_TIMEOUT='0.02') as client:
            try:
                first = await client.get('/store/products')
                second = await client.get('/store/collections')
                self.assertEqual((first.status_code, second.status_code), (200, 200))
                self.assertTrue(entered.is_set())
                self.assertFalse(release.is_set())
            finally:
                release.set()
                await gateway.app.state.analysis_task
        self.assertEqual(len(model.samples), 1)  # 第二筆略過，不偷偷堆進背景佇列。

    async def test_prediction_error_does_not_block_forwarding(self):
        model = Predictor()
        model.predict = lambda _: (_ for _ in ()).throw(ValueError('private-password'))
        with self.assertLogs(gateway.log) as logs:
            async with running(lambda r: reply(), model) as client:
                response = await client.get('/store/products')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('private-password', str(logs.output))

    async def test_upstream_failure_statuses(self):
        async with running(lambda r: reply(500)) as client:
            self.assertIsNone(gateway.app.state.predictor)
            self.assertEqual((await client.get('/store/products')).status_code, 500)
        for exception, expected in [(httpx.ReadTimeout, 504), (httpx.ConnectError, 502)]:
            def backend(request):
                raise exception('private-upstream-error', request=request)
            async with running(backend) as client:
                response = await client.get('/store/products')
                self.assertEqual(response.status_code, expected)
                self.assertNotIn('private-', response.text)

    async def test_form_binary_and_malformed_json(self):
        model = Predictor()
        async with running(lambda r: reply(), model) as client:
            await client.post('/store/carts', content='tag=a&tag=b&password=private-value',
                              headers={'Content-Type': 'application/x-www-form-urlencoded'})
            await client.post('/store/carts', content='{"note": "<script>"', headers={'Content-Type': 'application/json'})
            await client.post('/store/carts', content=b'\xff\x00', headers={'Content-Type': 'application/octet-stream'})
        self.assertEqual(model.samples[0]['body']['tag'], ['a', 'b'])
        self.assertNotIn('private-value', str(model.samples[0]))
        self.assertEqual(model.samples[1]['raw_body'], '{"note": "<script>"')
        self.assertIsNone(model.samples[2]['raw_body'])
        self.assertEqual(model.samples[2]['body']['unsupported_binary_bytes'], 2)

    async def test_invalid_configuration_and_model_failure(self):
        for url in ['ftp://backend.test', 'http://user:secret@backend.test', 'http://backend.test/api', 'http://backend.test/?key=value']:
            with self.assertRaises(ValueError):
                async with running(lambda r: reply(), MEDUSA_UPSTREAM=url):
                    pass
        model = Predictor()
        model.self_test = lambda: (_ for _ in ()).throw(ValueError('private-secret'))
        with self.assertLogs(gateway.log) as logs:
            async with running(lambda r: reply(), model) as client:
                self.assertIsNone(gateway.app.state.predictor)
                self.assertEqual((await client.get('/store/products')).status_code, 200)
        self.assertNotIn('private-secret', str(logs.output))


if __name__ == '__main__':
    unittest.main()
