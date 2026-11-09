"""正常填值規則、來源真實性與資料集修正追溯，不以評估分數當測試目標。"""
from pathlib import Path
import csv,copy,json,re,sys
import unittest
from collections import defaultdict
from document_values import violations,audit_document_values
from data_io import read_rows
from preflight import inspect_dataset
from train import groups
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'sentinel/dataset'))
from build_small_dataset import initial_value
DATA=ROOT/'sentinel/dataset/small-api-v7'
OLD=ROOT/'sentinel/dataset/small-api-v6-annotated'


class DocumentValueTests(unittest.TestCase):
    def test_regex_date_url_enum_types_and_no_fallback(self):
        spec={'type':'string','values':'正規表達式：`^[0-9a-f]{32}$`','meaning':'語言ID'}
        self.assertIn('pattern',violations('MSDSS cotton','header','sw-language-id',spec))
        self.assertFalse(violations('2fbb5fe2e29a4d70aa5854ce7ce3e20b','header','sw-language-id',spec))
        self.assertIn('date',violations('1999-14-90','body','dateOfBirth',dict(spec,values='格式：`"date"`')))
        self.assertIn('url',violations('hello','body','paymentSuccessUrl',dict(spec,values='')))
        self.assertIn('最小值',violations(0,'body','quantity',dict(spec,type='integer',values='最小值：`1`')))
        self.assertIn('max_length',violations('abcde','body','email',dict(spec,values='最多字元數：`4`')))
        self.assertIn('compressed_criteria_format',violations('H4sBad','query','_criteria',dict(spec,values='格式：`base64url(gzip(json_encode(criteria)))`')))
        self.assertIn('enum',violations('SESSION','header','sw-context-source',dict(spec,values='固定值：`session`')))
        self.assertFalse(violations([{'field':'id','order':'ASC'}],'body','sort',dict(spec,type='array',values='固定值：`ASC`、`DESC`')))
        self.assertFalse(violations('true','header','sw-include-seo-urls',dict(spec,type='boolean',values='',meaning='是否帶網址')))
        with self.assertRaises(ValueError):initial_value('body','unknown_field',{'values':'','type':'string'})

    def test_normal_values_conform_and_are_diverse(self):
        sets={s:read_rows(DATA/(s+'.csv')) for s in ('train','test','validation','challenge')}
        self.assertEqual(audit_document_values(DATA,sets),[])
        public=json.loads((DATA/'historical-public-values.json').read_text(encoding='utf-8'))
        counts=0;values=defaultdict(set)
        def walk(value):
            if isinstance(value,dict):
                for v in value.values():walk(v)
            elif isinstance(value,list):
                for v in value:walk(v)
            else:self.assertNotEqual(value,'MSDSS cotton')
        for rows in sets.values():
            for r in rows:
                walk(r['input'])
                if r['annotation']['proposed_label']!='normal':continue
                h=r['input']['headers']
                if 'sw-language-id' in h:
                    counts+=1;self.assertIn(h['sw-language-id'],public['language_ids']);self.assertRegex(h['sw-language-id'],r'^[0-9a-f]{32}$')
                body=r['input']['body']
                if isinstance(body,dict):
                    for k in ('companyName','department','dateOfBirth','term','query','zipcode'):
                        if isinstance(body.get(k),str):values[k].add(body[k])
                    self.assertFalse(any('〈' in k for k in body))
        self.assertEqual(counts,111)
        for k in ('companyName','department','dateOfBirth','term','query','zipcode'):self.assertGreater(len(values[k]),1,k)

    def test_original_payload_labels_and_split_unchanged(self):
        for split in ('train','test','validation','challenge'):
            old={r['sample_id']:r for r in read_rows(OLD/(split+'.csv'))};rows=read_rows(DATA/(split+'.csv'))
            self.assertEqual(len(rows),len(old))
            for r in rows:
                source=old[r['metadata']['source_sample_id']]
                self.assertEqual(r['annotation']['proposed_label'],source['annotation']['proposed_label'])
                self.assertEqual(r['metadata']['split'],source['metadata']['split'])
                self.assertEqual(r['metadata'].get('payload'),source['metadata'].get('payload'))
                self.assertEqual(r['metadata'].get('skeleton_group_id'),source['metadata'].get('skeleton_group_id'))
                self.assertFalse(r['metadata']['http_executed']);self.assertFalse(r['metadata']['business_verified'])

    def test_preflight_and_broken_normal_rule_rejected(self):
        sets,_,_,_,report=inspect_dataset(DATA,groups,offline=True,evidence_root=ROOT)
        self.assertTrue(report['ready'],report['errors'])
        changed=copy.deepcopy(sets)
        row=next(r for r in changed['train'] if r['annotation']['proposed_label']=='normal' and 'sw-language-id' in r['input']['headers'])
        row['input']['headers']['sw-language-id']='not-a-language-id'
        self.assertTrue(audit_document_values(DATA,changed))


if __name__=='__main__':unittest.main()
