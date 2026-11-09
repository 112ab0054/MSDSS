"""Train-only補強的資料完整性與隔離回歸測試，不以模型分數當測試條件。"""
import copy
import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from collections import Counter,defaultdict
from data_io import read_rows
from preflight import inspect_dataset
from train import groups
from skeletons import audit_dataset,group_catalog
from features import signals
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'sentinel/dataset'))
from build_small_dataset import field_value
from build_train_v5 import filter_candidates,SQL
OLD=ROOT/'sentinel/dataset/small-api-v4'
DATA=ROOT/'sentinel/dataset/small-api-v5'


class TrainingAugmentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sets={s:read_rows(DATA/(s+'.csv')) for s in ('train','test','validation','challenge')}
        cls.saved=json.loads((DATA/'provenance.json').read_text(encoding='utf-8'))

    def test_holdouts_are_byte_identical_and_original_train_preserved(self):
        for split in ('test','validation','challenge'):
            self.assertEqual((DATA/(split+'.csv')).read_bytes(),(OLD/(split+'.csv')).read_bytes())
        self.assertEqual(self.sets['train'][:450],read_rows(OLD/'train.csv'))
        self.assertEqual(Counter(r['annotation']['proposed_label'] for r in self.sets['train']),{'normal':198,'sqli':198,'xss':198})

    def test_new_pairs_are_balanced_raw_and_documented(self):
        extra=self.sets['train'][450:];pairs=defaultdict(list);locations=Counter()
        with (DATA/'augmentation-bindings.csv').open(encoding='utf-8-sig',newline='') as f:bindings={r['sample_id']:r for r in csv.DictReader(f)}
        for r in extra:
            m=r['metadata'];pairs[m['pair_group']].append(r)
            self.assertFalse(m['http_executed']);self.assertNotEqual(m['platform'],'medusa')
            if m.get('payload'):
                locations[r['annotation']['proposed_label'],m['target_location']]+=1
                self.assertEqual(field_value(r['input'],m['target_location'],m['target_parameter']),(True,m['payload']['value']))
                self.assertTrue(bindings[r['sample_id']]['document_meaning'])
                if r['annotation']['proposed_label']=='sqli':self.assertEqual(signals(m['payload']['value'])[12],0)
        self.assertEqual(len(pairs),48)
        for triple in pairs.values():
            self.assertEqual({r['annotation']['proposed_label'] for r in triple},{'normal','sqli','xss'})
            normal=next(r for r in triple if r['annotation']['proposed_label']=='normal')
        self.assertTrue(all(locations[label,loc]==12 for label in ('sqli','xss') for loc in ('header','body','query','path')))
        requests=[json.dumps(r['input'],sort_keys=True,ensure_ascii=False) for rows in self.sets.values() for r in rows]
        self.assertEqual(len(requests),len(set(requests)))

    def test_global_catalogue_and_document_fingerprints_pass(self):
        self.assertEqual(audit_dataset(DATA,self.sets,self.saved),[])
        _,_,_,_,report=inspect_dataset(DATA,groups,offline=True,evidence_root=ROOT)
        self.assertTrue(report['ready'],report['errors'])
        self.assertEqual(set(report['document_snapshots'].values()),{'match'})
        with (DATA/'field-coverage.csv').open(encoding='utf-8-sig',newline='') as f:coverage=list(csv.DictReader(f))
        self.assertEqual(len(coverage),620)
        self.assertTrue(all(int(r['存在筆數'])>0 for r in coverage))

    def test_frozen_holdout_marker_cannot_be_silently_changed(self):
        with tempfile.TemporaryDirectory(prefix='msdss-v5-frozen-test-') as tmp:
            tmp=Path(tmp).resolve();self.assertTrue(tmp.is_relative_to(Path(tempfile.gettempdir()).resolve()))
            for p in DATA.iterdir():
                if p.is_file() and p.name in ('train.csv','test.csv','validation.csv','challenge.csv','skeleton-catalog.csv'):(tmp/p.name).write_bytes(p.read_bytes())
            saved=copy.deepcopy(self.saved);saved['frozen_holdout_sha256']['test']='changed'
            (tmp/'provenance.json').write_text(json.dumps(saved),encoding='utf-8')
            _,_,_,_,report=inspect_dataset(tmp,groups,offline=True)
            self.assertFalse(report['ready'])
            self.assertIn('保留集與凍結指紋不符：test',report['errors'])

    def test_candidate_matching_existing_skeleton_is_rejected(self):
        candidate={'class':'sqli','value':SQL[0],'family':'sqli.train-v5-curated','template':'reserved','source':'reserved'}
        g,s=group_catalog([dict(candidate,label='sqli')]);candidate.update(skeleton_group_id=g[0],skeleton_signature=s[0])
        _,_,decisions=filter_candidates([candidate])
        self.assertEqual(next(r for r in decisions if r['value']==SQL[0])['decision'],'existing_skeleton_overlap')


if __name__=='__main__':unittest.main()
