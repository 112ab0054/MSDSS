"""Document coverage and split integrity, independent of any classifier score."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
import unittest
from build_small_dataset import read_documents, field_value

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'sentinel/dataset/small-api-v3'


class V3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sets={}
        for s in ('train','test','validation','challenge'):
            with (DATA/(s+'.csv')).open(encoding='utf-8-sig',newline='') as f:
                cls.sets[s]=[json.loads(r['完整紀錄JSON']) for r in csv.DictReader(f)]
        cls.provenance=json.loads((DATA/'provenance.json').read_text(encoding='utf-8'))

    def test_size_classes_locations_and_platforms(self):
        for s,n in [('train',450),('test',150),('validation',150),('challenge',96)]:
            rows=self.sets[s]
            self.assertEqual(len(rows),n)
            self.assertEqual({r['metadata']['platform'] for r in rows},{'sylius'} if s=='validation' else {'bagisto','shopware'})
            for label in ('normal','sqli','xss'):
                self.assertEqual(sum(r['annotation']['proposed_label']==label for r in rows),n//3)
            for label in ('sqli','xss'):
                counts=[sum(r['annotation']['proposed_label']==label and r['metadata']['target_location']==loc for r in rows)
                        for loc in ('header','body','query','path')]
                self.assertLessEqual(max(counts)-min(counts),1)

    def test_no_cross_split_templates_values_operations_or_requests(self):
        for a,b in itertools.combinations(self.sets,2):
            for value in ('template','value'):
                values=lambda s:{r['metadata']['payload'][value] for r in self.sets[s] if r['metadata']['payload']}
                self.assertFalse(values(a)&values(b))
            operations=lambda s:{(r['metadata']['platform'],r['input']['method'],r['metadata']['operation_path']) for r in self.sets[s]}
            self.assertFalse(operations(a)&operations(b))
        requests=[json.dumps(r['input'],sort_keys=True) for rows in self.sets.values() for r in rows]
        self.assertEqual(len(requests),len(set(requests)))

    def test_known_and_unknown_families_are_different_experiments(self):
        for label in ('sqli','xss'):
            families=lambda s:{r['metadata']['payload']['family'] for r in self.sets[s] if r['annotation']['proposed_label']==label}
            self.assertTrue(families('test')<=families('train'))
            self.assertFalse(families('challenge')&(families('test')|families('train')))
        old_test={'";void(0);//',"';void(0);//",'${void(0)}'}
        self.assertFalse(old_test & {r['metadata']['payload']['value'] for r in self.sets['train'] if r['metadata']['payload']})

    def test_all_document_fields_present_and_targets_declared(self):
        ops,hashes=read_documents()
        self.assertEqual(hashes,self.provenance['parameter_document_sha256'])
        all_rows=[r for rows in self.sets.values() for r in rows]
        self.assertEqual(len(ops),62)
        count=0
        for key,op in ops.items():
            rows=[r for r in all_rows if (r['metadata']['platform'],r['input']['method'],r['metadata']['operation_path'])==key]
            for (loc,name),spec in op['fields'].items():
                count+=1
                self.assertTrue(any(name=='（本文）' or field_value(r['input'],loc,name)[0] for r in rows))
            for r in rows:
                if r['metadata']['payload']:
                    self.assertIn((r['metadata']['target_location'],r['metadata']['target_parameter']),op['fields'])
        self.assertEqual(count,620)

    def test_matched_triplets_raw_content_and_no_fake_http(self):
        for rows in self.sets.values():
            pairs={}
            for row in rows:
                m=row['metadata'];pairs.setdefault(m['pair_group'],[]).append(row)
                self.assertFalse(m['http_executed']);self.assertIsNone(m['session_group'])
                self.assertIsNone(m['source_evidence'])
                req=row['input']
                self.assertEqual(json.loads(req['raw_body']) if req['raw_body'] else None,req['body'])
            for triple in pairs.values():
                self.assertEqual(len(triple),3)
                normal=next(r for r in triple if r['annotation']['proposed_label']=='normal')
                for row in triple:
                    self.assertEqual(set(row['input']['headers']),set(normal['input']['headers']))
                    if row is not normal:self.assertEqual(row['metadata']['control_sample_id'],normal['sample_id'])


if __name__=='__main__':unittest.main()
