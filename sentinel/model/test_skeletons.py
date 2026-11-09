"""骨架切分的正反例、資料覆蓋與防止只換ID繞過的回歸測試。"""
import copy
import csv
import hashlib
import json
from pathlib import Path
import sys
import unittest
from skeletons import signature, group_catalog, audit_dataset, PROTOCOL
from data_io import read_rows
from preflight import inspect_dataset
from train import groups
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'sentinel/dataset/small-api-v4'
sys.path.insert(0,str(ROOT/'sentinel/dataset'))


class SkeletonTests(unittest.TestCase):
    def test_literal_alias_and_encoding_siblings(self):
        examples=[('sqli',"' AND SLEEP(0)=0 -- ","' AND SLEEP(0.05)=0 -- "),
                  ('sqli',"' OR 1=1 -- ","' OR 'a'='a' -- "),
                  ('xss','<script>console.info("catalog")</script>','<ScRiPt>console.log("product")</ScRiPt>'),
                  ('xss','<script>console.info(1)</script>','%253Cscript%253Econsole.info(7)%253C/script%253E'),
                  ('xss','<script>console.info(1)</script>','&#60;script&#62;console.info("encoded")&#60;/script&#62;')]
        for label,a,b in examples:
            with self.subTest(a=a):self.assertEqual(signature(a,label),signature(b,label))

    def test_unclosed_comment_cdata_has_frozen_signature(self):
        # CPython 3.13's stdlib HTMLParser differs from 3.11 on this real external payload.
        value='<!--<value><![cdata[<xml id=i><x><c><![cdata[<img id=xss src="javas<![cdata[cript:alert(\'xss\');">'
        with (DATA/'skeleton-catalog.csv').open(encoding='utf-8-sig',newline='') as f:
            entry=next(r for r in csv.DictReader(f) if r['value']==value)
        self.assertEqual(signature(value,'xss'),entry['skeleton_signature'])
        self.assertEqual(json.loads(signature(value,'xss'))[0],'HTML')

    def test_parser_mismatch_fails_closed(self):
        saved=copy.deepcopy(self.saved);saved['skeleton_parser']['id']='different-parser'
        self.assertTrue(any('解析器版本' in e for e in audit_dataset(DATA,self.sets,saved)))


    def test_distinct_structure_is_not_identical(self):
        self.assertNotEqual(signature("' AND SLEEP(1)=0 -- ",'sqli'),signature("' UNION SELECT 1 -- ",'sqli'))
        self.assertNotEqual(signature('<script>console.info(1)</script>','xss'),signature('<img onerror="console.info(1)">','xss'))

    def test_global_allocation_keeps_siblings_and_external_reserved(self):
        from build_skeleton_v4 import allocate_catalog
        a={'value':'<script>console.info(1)</script>','family':'a','template':'a','source':'local'}
        b=dict(a,value='&#60;script&#62;console.log(2)&#60;/script&#62;',template='b',family='different')
        # Supply sufficient other structures for a train/test allocation.
        local={s:{l:[] for l in ('sqli','xss')} for s in ('train','test','challenge')}
        local['train']['xss']=[a,dict(a,value='${console.info(1)}',template='c'),dict(a,value='<svg onload="console.info(1)"></svg>',template='d')]
        local['challenge']['xss']=[b]
        local['train']['sqli']=[dict(a,value=v,template=str(i),family='sql') for i,v in enumerate(['UNION SELECT 1','AND SLEEP(1)','ORDER BY name'])]
        external={'normal':[],'sqli':[dict(a,value='UNION SELECT 9',template='external',family=None,source='httpParamsDataset')],'xss':[]}
        cases,ext,catalog=allocate_catalog(local,external)
        same=[c for c in catalog if c['template'] in ('a','b') and c['class']=='xss']
        self.assertEqual({c['assigned_split'] for c in same},{'challenge'})
        self.assertEqual(len({c['skeleton_group_id'] for c in same}),1)
        self.assertEqual(sum(c['excluded_local_overlap'] for c in catalog),1)
        self.assertEqual(ext['sqli'][0]['value'],'UNION SELECT 9')
        self.assertEqual(a['value'],'<script>console.info(1)</script>')

    @classmethod
    def setUpClass(cls):
        cls.sets={s:read_rows(DATA/(s+'.csv')) for s in ('train','test','validation','challenge')}
        cls.saved=json.loads((DATA/'provenance.json').read_text(encoding='utf-8'))

    def test_real_dataset_recomputed_and_complete(self):
        self.assertEqual(audit_dataset(DATA,self.sets,self.saved),[])
        _,_,_,_,report=inspect_dataset(DATA,groups,offline=True,evidence_root=ROOT)
        self.assertTrue(report['ready'],report['errors'])
        self.assertEqual(set(report['document_snapshots'].values()),{'match'})
        with (DATA/'field-coverage.csv').open(encoding='utf-8-sig',newline='') as f:coverage=list(csv.DictReader(f))
        self.assertEqual(len(coverage),620)
        self.assertTrue(all(int(c['存在筆數'])>0 for c in coverage))
        for split,rows in self.sets.items():
            self.assertEqual(len(rows),{'train':450,'test':150,'validation':150,'challenge':96}[split])
            self.assertTrue(all(not r['metadata']['http_executed'] for r in rows))
            self.assertTrue(all(r['metadata']['platform']!='medusa' for r in rows))
            self.assertTrue(all(r['metadata']['evaluation_protocol']==PROTOCOL for r in rows))
            pairs={}
            for r in rows:pairs.setdefault(r['metadata']['pair_group'],[]).append(r)
            self.assertTrue(all({r['annotation']['proposed_label'] for r in rs}=={'normal','sqli','xss'} for rs in pairs.values()))

    def test_raw_payloads_and_auxiliary_grouping_do_not_rewrite_requests(self):
        from build_small_dataset import field_value
        before=json.dumps(self.sets,ensure_ascii=False,sort_keys=True)
        self.assertEqual(audit_dataset(DATA,self.sets,self.saved),[])
        self.assertEqual(before,json.dumps(self.sets,ensure_ascii=False,sort_keys=True))
        for rows in self.sets.values():
            for row in rows:
                req=row['input'];meta=row['metadata'];payload=meta.get('payload')
                if payload:
                    present,value=field_value(req,meta['target_location'],meta['target_parameter'])
                    self.assertTrue(present)
                    self.assertEqual(value,payload['value'])
                if req['raw_body']:
                    self.assertEqual(json.loads(req['raw_body']),req['body'])

    def test_changing_ids_does_not_hide_same_skeleton(self):
        sets=copy.deepcopy(self.sets)
        source=next(r for r in sets['train'] if r['metadata'].get('payload'))
        moved=copy.deepcopy(source);moved['sample_id']='different-id';moved['metadata']['split']='test'
        moved['metadata']['skeleton_group_id']='different-group';moved['metadata']['template_id']='different-template'
        sets['test'].append(moved)
        errors=audit_dataset(DATA,sets,self.saved)
        self.assertTrue(any('實際資料含跨集合骨架' in e for e in errors),errors)

    def test_metadata_and_catalogue_hash_tampering_rejected(self):
        sets=copy.deepcopy(self.sets)
        row=next(r for r in sets['test'] if r['metadata'].get('payload'))
        row['metadata']['skeleton_signature']='fake'
        self.assertTrue(any('骨架標記' in e for e in audit_dataset(DATA,sets,self.saved)))
        self.assertIn('骨架目錄 SHA256 不符',audit_dataset(DATA,self.sets,dict(self.saved,skeleton_catalog_sha256='fake')))


if __name__=='__main__':unittest.main()
