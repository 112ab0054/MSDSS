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
        self.assertEqual(len(features(base)), 140)
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
        self.assertNotEqual(features({'path_parameters': {'slug': 'shirt'}}),
                            features({'path_parameters': {'slug': "' OR 'a'='a' --"}}))

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
            by_operation[(row["metadata"]["platform"], row["input"]["method"], row["input"]["path"])].append(row)
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
        """訓練後搬移模型，確認從其他工作目錄仍可推論。"""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            data = tmp / "data.csv"
            with data.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["完整紀錄JSON"])
                writer.writeheader()
                # 每個平台建立獨立 session，每組都有三類合成樣本。
                for platform in ["bagisto", "shopware", "sylius"]:
                    for session in range(12):
                        for label, payload in [("normal", "shirt"), ("sqli", "' union select --"),
                                               ("xss", '<script>alert(1)</script>')]:
                            row = {"input": {"method": "GET", "query": {
                                "q": payload, "nonce": f"{platform}-{session}-{label}"}},
                                "annotation": {"label": label}, "metadata": {
                                    "platform": platform, "session_group": f"{platform}-{session}",
                                    "training_approved": True, "request_input_version": 2}}
                            writer.writerow({"完整紀錄JSON": json.dumps(row)})
            result = subprocess.run([sys.executable, str(ROOT / "train.py"), str(data),
                                     "--output", str(tmp / "original")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            # 搬到含中文與空白的目錄，並使用與程式不同的工作目錄。
            report = json.loads((tmp / "original" / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["audit"]["group_overlap"], 0)
            self.assertIn("majority_baseline", report)
            self.assertTrue((tmp / "original" / "predictions.csv").exists())
            self.assertTrue((tmp / "original" / "split.csv").exists())
            self.assertTrue((tmp / "original" / "report.md").exists())
            moved = tmp / "搬移 model"
            moved.mkdir()
            for name in ["features.py", "predict.py"]:
                shutil.copy(ROOT / name, moved)
            shutil.move(str(tmp / "original"), moved / "artifacts")
            request = tmp / "request.json"
            request.write_text('{"method":"GET","query":{"q":"shirt"}}')
            result = subprocess.run([sys.executable, str(moved / "predict.py"), str(request)],
                                    cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(json.loads(result.stdout)["label"], ["normal", "sqli", "xss"])


if __name__ == "__main__":
    unittest.main()
