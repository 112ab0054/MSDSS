"""確認三類傳輸header補強對稱，並保留原文與凍結題。"""
import csv,json
from pathlib import Path
from collections import Counter,defaultdict
import unittest
from data_io import read_rows
from preflight import inspect_dataset
from train import groups
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'sentinel/dataset/small-api-v6'


class TransportTests(unittest.TestCase):
    def test_original_train_and_all_holdouts_unchanged(self):
        old=ROOT/'sentinel/dataset/small-api-v5'
        rows=read_rows(DATA/'train.csv')
        self.assertEqual(rows[:594],read_rows(old/'train.csv'))
        for split in ('test','validation','challenge'):self.assertEqual((DATA/(split+'.csv')).read_bytes(),(old/(split+'.csv')).read_bytes())
        self.assertEqual(Counter(r['annotation']['proposed_label'] for r in rows),{'normal':234,'sqli':234,'xss':234})

    def test_same_profiles_for_all_labels_and_original_payloads(self):
        rows=read_rows(DATA/'train.csv');old={r['sample_id']:r for r in rows[:594]};extra=rows[594:]
        count=Counter();pairs=defaultdict(list)
        for r in extra:
            m=r['metadata'];source=old[m['original_train_sample_id']]
            count[m['transport_profile'],r['annotation']['proposed_label']]+=1;pairs[m['pair_group']].append(r)
            for key in ('path','raw_query','raw_body','body','query'):
                self.assertEqual(r['input'][key],source['input'][key])
            self.assertEqual(m.get('payload'),source['metadata'].get('payload'))
            self.assertFalse(m['http_executed']);self.assertNotEqual(m['platform'],'medusa')
        self.assertEqual(len(count),12);self.assertTrue(all(v==9 for v in count.values()))
        self.assertEqual(len(pairs),36)
        for values in pairs.values():
            self.assertEqual({v['annotation']['proposed_label'] for v in values},{'normal','sqli','xss'})
            self.assertEqual(len({v['input']['headers']['Accept'] for v in values}),1)

    def test_preflight_and_document_coverage(self):
        _,_,_,_,report=inspect_dataset(DATA,groups,offline=True,evidence_root=ROOT)
        self.assertTrue(report['ready'],report['errors'])
        self.assertEqual(set(report['document_snapshots'].values()),{'match'})
        with (DATA/'field-coverage.csv').open(encoding='utf-8-sig',newline='') as f:coverage=list(csv.DictReader(f))
        self.assertEqual(len(coverage),620);self.assertTrue(all(int(r['存在筆數']) for r in coverage))


if __name__=='__main__':unittest.main()
