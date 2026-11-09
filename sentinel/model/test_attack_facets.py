"""面向欄只供顯示，原始紀錄、分組、模型輸入與baseline不可變。"""
import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from data_io import read_rows
from preflight import inspect_dataset
from train import groups
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'sentinel/dataset'))
from annotate_attack_facets import attack_facets,COLUMN
OLD=ROOT/'sentinel/dataset/small-api-v6'
NEW=ROOT/'sentinel/dataset/small-api-v6-annotated'


def sample(label,value,family=None):
    return {'annotation':{'proposed_label':label},'metadata':{'payload':{'value':value,'family':family}}}


class AttackFacetTests(unittest.TestCase):
    def test_multiple_tags_and_encoded_source(self):
        tags=attack_facets(sample('sqli',"' UNION SELECT SLEEP(1)"))
        self.assertIn('UNION聯集',tags);self.assertIn('SELECT／子查詢',tags);self.assertIn('時間／高耗時相關',tags)
        tags=attack_facets(sample('xss','&lt;script&gt;alert(1)&lt;/script&gt;'))
        self.assertIn('script標籤',tags);self.assertIn('原文編碼變體',tags)
        self.assertEqual(attack_facets(sample('normal','<script>alert(1)</script>')),['不適用'])
        self.assertIn('外部資源載入（XSS標註待確認）',attack_facets(sample('xss','<img src="http://example.invalid/p.png">')))

    def test_all_original_cells_and_model_rows_unchanged(self):
        count=0
        for split in ('train','test','validation','challenge'):
            with (OLD/(split+'.csv')).open(encoding='utf-8-sig',newline='') as f:old=list(csv.DictReader(f))
            with (NEW/(split+'.csv')).open(encoding='utf-8-sig',newline='') as f:new=list(csv.DictReader(f))
            self.assertEqual(old,[{k:v for k,v in r.items() if k!=COLUMN} for r in new])
            self.assertTrue(all(r[COLUMN] for r in new));count+=len(new)
            self.assertEqual(read_rows(OLD/(split+'.csv')),read_rows(NEW/(split+'.csv')))
        self.assertEqual(count,1098)

    def test_preflight_accepts_explicit_new_hashes(self):
        _,_,_,_,report=inspect_dataset(NEW,groups,offline=True,evidence_root=ROOT)
        self.assertTrue(report['ready'],report['errors'])
        saved=json.loads((NEW/'provenance.json').read_text(encoding='utf-8'))
        self.assertFalse(saved['display_annotation']['used_as_model_feature'])
        for split in ('test','validation','challenge'):
            self.assertEqual(saved['unannotated_holdout_sha256'][split],hashlib.sha256((OLD/(split+'.csv')).read_bytes()).hexdigest())
            self.assertEqual(saved['frozen_holdout_sha256'][split],hashlib.sha256((NEW/(split+'.csv')).read_bytes()).hexdigest())

    def test_display_column_cannot_leak_into_training_rows(self):
        with tempfile.TemporaryDirectory(prefix='msdss-facet-display-') as temp:
            temp=Path(temp).resolve();self.assertTrue(temp.is_relative_to(Path(tempfile.gettempdir()).resolve()))
            with (NEW/'test.csv').open(encoding='utf-8-sig',newline='') as f:
                reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
            original=read_rows(NEW/'test.csv')
            for row in rows:row[COLUMN]='deliberately wrong display label'
            with (temp/'test.csv').open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
            self.assertEqual(read_rows(temp/'test.csv'),original)


if __name__=='__main__':unittest.main()
