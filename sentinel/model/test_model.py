"""用合成資料驗證程式流程；測試通過不代表真實攻擊辨識準確。"""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from evaluate import metrics, cluster_interval
from features import features
from header_contracts import documented_headers
from request_input import prepare_request, from_evidence, redact_json_text
from train import groups

ROOT = Path(__file__).resolve().parent


class ModelTests(unittest.TestCase):
    def test_transitive_groups(self):
        """確認間接相連的請求會合併，獨立請求仍保持分開。"""
        rows = [{"input": {"query": {"q": str(i)}}, "metadata": meta} for i, meta in enumerate([
            {"session_group": "a", "near_fingerprint": "x"},
            {"session_group": "b", "near_fingerprint": "x"},
            {"session_group": "b"}, {"session_group": "c"}])]
        group = groups(rows)
        self.assertEqual(group[0], group[2])
        self.assertNotEqual(group[0], group[3])

    def test_credentials_excluded(self):
        """更換密碼內容不應改變輸入模型的特徵。"""
        self.assertEqual(features({"body": {"password": "abc"}}),
                         features({"body": {"password": "' OR 1=1"}}))

    def test_header_features(self):
        """header 攻擊會影響特徵；大小寫不影響結果，憑證內容不進特徵。"""
        base = {"headers": {"X-Locale": "en", "Authorization": "abc"}}
        attack = {"headers": {"X-Locale": "<script>void(0)</script>", "Authorization": "abc"}}
        names, _ = documented_headers()
        self.assertEqual(len(features(base)), 74 + 17 * len(names))
        self.assertNotEqual(features(base), features(attack))
        self.assertEqual(features(base), features({"headers": {"x-locale": "en", "authorization": "xyz"}}))
        self.assertEqual(features({"headers": {"Host": "a.example"}}),
                         features({"headers": {"Host": "b.example"}}))

    def test_all_request_locations(self):
        """任意新增欄位與非 JSON 本文都參與特徵，不只取搜尋／姓名。"""
        for key in ['order', 'page', 'per_page', 'type', 'unexpected']:
            self.assertNotEqual(features({'query': {key: 'normal'}}),
                                features({'query': {key: "' UNION SELECT NULL --"}}))
        self.assertNotEqual(features({'body': {'nested': {'extra': 'ok'}}}),
                            features({'body': {'nested': {'extra': '<script>void(0)</script>'}}}))
        self.assertNotEqual(features({'body': 'plain text'}), features({'body': '<script>void(0)</script>'}))
        self.assertNotEqual(features({'path': '/products/shirt'}),
                            features({'path': '/products/1%20OR%201=1'}))

    def test_raw_input_values_and_encoding_are_preserved(self):
        raw = ' { "productId" : "1 OR 1=1", "isValid": true, "email":"user@example.test", "password" : "private-value" } '
        expected = raw.replace('"private-value"', '"[REDACTED]"')
        self.assertEqual(redact_json_text(raw), expected)
        row = {'method':'POST','path':'/products/1%20OR%201=1?q=A%2fb&q=A+B',
            'operation_path':'/products/{id}','request_headers':{'Content-Type':'application/json','X-Request-ID':'real-id','Host':'example.test'},
            'request_body':json.loads(raw),'request_body_raw':raw}
        result = from_evidence(row)
        self.assertEqual(result['path'],'/products/1%20OR%201=1')
        self.assertEqual(result['raw_query'],'q=A%2fb&q=A+B')
        self.assertEqual(result['raw_body'],expected)
        self.assertEqual(result['body']['isValid'],True)
        self.assertEqual(result['body']['productId'],'1 OR 1=1')
        self.assertEqual(result['headers']['X-Request-ID'],'real-id')
        self.assertEqual(result['headers']['Host'],'example.test')

    def test_every_documented_header_has_an_individual_slot(self):
        names, sources = documented_headers()
        self.assertEqual(len(names),12);self.assertEqual(len(sources),3)
        from features import SENSITIVE, header_features
        for index,name in enumerate(names):
            base=header_features({},names);present=header_features({name:'en'},names)
            start=18+17*index
            self.assertEqual(base[start],0);self.assertEqual(present[start],1)
            if not SENSITIVE.search(name):
                attack=header_features({name:'<script>void(0)</script>'},names)
                self.assertNotEqual(present[start:start+17],attack[start:start+17])

    def test_query_credentials_masked_without_reformatting_other_values(self):
        result=prepare_request({'path':'/products/123','raw_query':'q=A%2fb&token=private-value&q=A+B','headers':{},'body':None})
        self.assertEqual(result['raw_query'],'q=A%2fb&token=[REDACTED]&q=A+B')
        no_type=prepare_request({'path':'/products','raw_body':' { "password":"private-value", "id":"actual-id" } ','headers':{}})
        self.assertEqual(no_type['raw_body'],' { "password":"[REDACTED]", "id":"actual-id" } ')

    def test_gateway_and_evidence_produce_the_same_raw_feature_vector(self):
        import importlib.util
        from types import SimpleNamespace
        from starlette.datastructures import Headers
        spec=importlib.util.spec_from_file_location('gateway_unit_fixture',ROOT.parent/'gateway/app.py')
        gateway=importlib.util.module_from_spec(spec);spec.loader.exec_module(gateway)
        raw=' { "productId":"1 OR 1=1", "email":"user@example.test", "password":"private-value" } '
        query='q=A%2fb&q=A+B&token=private-value'
        headers={'Content-Type':'application/json','Host':'127.0.0.1:18081','X-Request-ID':'original-request-id','X-Locale':'en'}
        row={'method':'POST','path':'/products/123?'+query,'operation_path':'/products/{id}',
            'request_target':'/api/shop/products/123?'+query,'raw_query':query,
            'request_headers':headers,'request_body':json.loads(raw),'request_body_raw':raw}
        request=SimpleNamespace(method='POST',headers=Headers(headers),url=SimpleNamespace(path='/api/shop/products/123'),
            scope={'raw_path':b'/api/shop/products/123','query_string':query.encode()})
        observed=gateway.model_request(request,raw.encode())
        training=from_evidence(row)
        self.assertEqual(training['raw_query'],observed['raw_query'])
        self.assertEqual(training['raw_body'],observed['raw_body'])
        self.assertEqual(features(training),features(observed))

    def test_document_candidates(self):
        """候選只能修改文件宣告的 header，且不能偽造 HTTP 或訓練核准。"""
        from generate_api_data import generate, ROOT as PROJECT
        rows, coverage = generate(PROJECT / "sentinel/dataset/reference/normal-candidates.csv")
        self.assertTrue(rows)
        self.assertEqual(len(coverage), 62)
        for row in rows:
            meta = row["metadata"]
            self.assertFalse(meta["http_executed"])
            self.assertFalse(meta["training_approved"])
            self.assertIsNone(meta["source_evidence"])
            self.assertTrue((PROJECT / meta["contract_file"]).exists())
            if meta["scenario_kind"] in {"attack_intent", "documented_value"}:
                self.assertIn(meta["target_parameter"], row["input"]["headers"])
        from collections import defaultdict
        by_operation = defaultdict(list)
        for row in rows:
            by_operation[(row["metadata"]["platform"], row["input"]["method"], row["metadata"]["operation_path"])].append(row)
        for detail in coverage:
            key = detail["platform"], detail["method"], detail["path"]
            planned = by_operation[key]
            optional = set(detail["optional_headers"])
            masks = {tuple(sorted(set(r["metadata"]["present_documented_headers"]) & optional))
                     for r in planned if r["metadata"]["scenario_kind"] == "optional_presence"}
            self.assertEqual(len(masks), 2 ** len(optional))
            for name, spec in detail["headers"].items():
                self.assertTrue(any(name in r["input"]["headers"] for r in planned))
                self.assertTrue(any(name not in r["input"]["headers"] for r in planned))
                for value in spec["values"]:
                    self.assertTrue(any(r["input"]["headers"].get(name) == value for r in planned))
                if spec["sensitive"]:
                    self.assertEqual(spec["values"], ["${LIVE:" + name + "}"])

    def test_metrics(self):
        """用可手算的錯誤驗證矩陣方向，以及誤報／漏報的分母。"""
        y = np.array([0, 0, 1, 1, 2, 2])
        probabilities = np.eye(3)[[0, 1, 0, 1, 2, 2]]
        report = metrics(y, probabilities)
        self.assertEqual(report["confusion_matrix"], [[1, 1, 0], [1, 1, 0], [0, 0, 2]])
        self.assertAlmostEqual(report["accuracy"], 4 / 6)
        self.assertAlmostEqual(report["normal_false_positive_rate"], 1 / 2)
        self.assertAlmostEqual(report["attack_miss_rate"], 1 / 4)
        self.assertAlmostEqual(report["attack_detection_recall"], 3 / 4)
        self.assertFalse(cluster_interval(y, probabilities, np.arange(6))["available"])

    def test_group_confidence_interval(self):
        """每組含三類且全部預測正確時，重抽樣區間應固定為 1。"""
        y = np.tile([0, 1, 2], 20)
        result = cluster_interval(y, np.eye(3)[y], np.repeat(np.arange(20), 3), repetitions=30)
        self.assertTrue(result["available"])
        self.assertEqual(result["macro_f1"], [1.0, 1.0])
        self.assertEqual(result["valid_repetitions"], 30)

    def test_train_and_relocate(self):
        from test_explicit_training import run_integration
        run_integration(self)

    def test_formal_training_rejects_uncaptured_raw_input(self):
        from data_io import validate_rows
        rows=[{'input':{},'metadata':{'platform':p,'session_group':p,'http_executed':True,
              'training_approved':True,'request_input_version':3,
              'raw_target_captured':False,'raw_body_captured':False}}
              for p in ('bagisto','shopware')]
        with self.assertRaisesRegex(ValueError,'原文'):
            validate_rows(rows,'train')


if __name__ == "__main__":
    unittest.main()
