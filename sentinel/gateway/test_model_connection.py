"""使用使用者提供的真實 XGBoost 權重測接線；HTTP 上游仍為模擬，不冒充 Medusa 實測。"""
from contextlib import asynccontextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import httpx
from xgboost import XGBClassifier

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('gateway_actual_model_test', HERE / 'app.py')
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)


@asynccontextmanager
async def connected(directory=None):
    """不替換 Predictor：讓 lifespan 真正載入權重、自測，再把網路換成可觀測上游。"""
    seen = []
    def backend(request):
        seen.append(request)
        return httpx.Response(200, stream=httpx.ByteStream(b'backend reached'))
    with patch.dict(os.environ, {'MEDUSA_UPSTREAM': 'http://medusa.test', 'GATEWAY_ANALYSIS_TIMEOUT': '2'}):
        if directory is None:
            os.environ.pop('GATEWAY_MODEL_DIR', None)  # 驗證不設參數時預設模型就會接上。
        else:
            os.environ['GATEWAY_MODEL_DIR'] = str(directory)
        async with gateway.app.router.lifespan_context(gateway.app):
            async with httpx.AsyncClient(transport=httpx.MockTransport(backend)) as upstream:
                gateway.app.state.client = upstream
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway.app), base_url='http://gateway.test') as client:
                    yield client, seen


class ActualModelConnectionTests(unittest.IsolatedAsyncioTestCase):
    def test_current_trained_bundle_is_intact(self):
        """模型與原清單逐檔核對，核對已授權重訓的v6套件與來源，避免混入舊權重。"""
        folder = gateway.DEFAULT_MODEL
        manifest = json.loads((folder / 'bundle-manifest.json').read_text())
        source = json.loads((HERE / 'model-source.json').read_text())
        for name, digest in manifest.items():
            self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), digest, name)
        self.assertEqual(hashlib.sha256((folder / 'model.json').read_bytes()).hexdigest(), source['model_sha256'])
        self.assertTrue(source['model_retrained'])
        self.assertEqual(source['feature_version'],6)
        self.assertFalse(source['platform_http_verified'])

    async def test_default_real_model_predicts_selected_requests_and_forwards_all(self):
        """完整接線：進站 bytes → 遮蔽副本 → 2402 維 → 真 XGBoost → 記錄機率 → 轉送。"""
        with self.assertLogs(gateway.log, level='INFO') as logs:
            async with connected() as (client, seen):
                predictor = gateway.app.state.predictor
                self.assertIsNotNone(predictor)
                self.assertIsInstance(predictor.model, XGBClassifier)
                self.assertEqual(predictor.feature_count, 2402)
                self.assertEqual((predictor.mode, predictor.exploratory), ('offline', True))
                original = predictor.predict
                # wraps 保留真正預測，只額外觀測呼叫次數，沒有捏造 normal/SQLi/XSS 結果。
                with patch.object(predictor, 'predict', wraps=original) as calls:
                    await client.get('/store/products?query=cotton&page=2')
                    await client.get('/store/products', params={'query': "' OR 1=1 --"})
                    raw = b'{"note":"<script>alert(1)</script>","password":"fixture-private"}'
                    await client.post('/store/carts', content=raw, headers={'Content-Type': 'application/json'})
                    await client.get('/outside-reference-77')
                    self.assertEqual(calls.call_count, 4)
                    samples = [call.args[0] for call in calls.call_args_list]
                expected = [original(sample) for sample in samples]
                self.assertEqual(len(seen), 4)
                self.assertEqual(seen[2].content, raw)  # 原密碼只交後端，不被副本的遮蔽值取代。
        predictions = [line for line in logs.output if 'prediction label=' in line]
        self.assertEqual(len(predictions), 4)
        for line, result in zip(predictions, expected):
            self.assertIn('mode=offline exploratory=True', line)
            self.assertIn('label=' + result['label'], line)
            self.assertEqual(json.loads(line.split('probabilities=', 1)[1]), result['probabilities'])
            self.assertAlmostEqual(sum(result['probabilities'].values()), 1, places=6)
        self.assertNotIn('fixture-private', str(logs.output) + str(samples))

    async def test_legitimate_accept_ranges_remain_visible_and_predict_normal(self):
        """針對已重現的Accept誤報作回歸，並確認原header仍送到後端。"""
        async with connected() as (client, seen):
            predictor=gateway.app.state.predictor
            original=predictor.predict
            with patch.object(predictor,'predict',wraps=original) as calls:
                for value in ('*/*','application/*','text/html,application/json;q=0.9,*/*;q=0.8'):
                    response=await client.get('/store/products?q=cotton',headers={'Accept':value})
                    self.assertEqual(response.status_code,200)
                    sample=calls.call_args.args[0]
                    self.assertEqual(sample['headers']['accept'],value)
                    self.assertEqual(original(sample)['label'],'normal')
                    self.assertEqual(seen[-1].headers['accept'],value)

    async def test_relocated_bundle_with_chinese_spaces_loads(self):
        """換到含中文與空白的目錄後仍可載入與推論，不依賴訓練機或目前 cwd 的路徑。"""
        with tempfile.TemporaryDirectory(prefix='msdss-relocated-model-') as temporary:
            moved = Path(temporary) / '中文 模型'
            shutil.copytree(gateway.DEFAULT_MODEL, moved)
            async with connected(moved) as (client, seen):
                self.assertIsNotNone(gateway.app.state.predictor)
                self.assertEqual((await client.get('/store/products')).status_code, 200)
                self.assertEqual(len(seen), 1)

    async def test_corrupt_bundle_does_not_pretend_detection_is_enabled(self):
        """SHA 不符必須記載入失敗；網站仍轉送，但不能假裝模型正常。"""
        with tempfile.TemporaryDirectory(prefix='msdss-corrupt-model-') as temporary:
            copied = Path(temporary) / 'model'
            shutil.copytree(gateway.DEFAULT_MODEL, copied)
            (copied / 'metadata.json').write_text('{}')
            with self.assertLogs(gateway.log) as logs:
                async with connected(copied) as (client, seen):
                    self.assertIsNone(gateway.app.state.predictor)
                    self.assertEqual((await client.get('/store/products')).status_code, 200)
                    self.assertEqual(len(seen), 1)
            self.assertTrue(any('model_load_failed' in line for line in logs.output))


if __name__ == '__main__':
    unittest.main()
