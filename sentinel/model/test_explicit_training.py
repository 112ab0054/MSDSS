"""Synthetic pipeline checks only; never research accuracy evidence."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from data_io import validate_rows
from request_input import redact_body_text

HERE = Path(__file__).resolve().parent


def run_integration(test):
    with tempfile.TemporaryDirectory(prefix='msdss-training-unit-') as tmp:
        tmp = Path(tmp).resolve()
        assert tmp.is_relative_to(Path(tempfile.gettempdir()).resolve())
        data = tmp / 'data'; data.mkdir()
        for split in ('train', 'test', 'validation'):
            platforms = ['sylius'] if split == 'validation' else ['bagisto', 'shopware']
            with (data / (split + '.csv')).open('w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f); writer.writerow(['完整紀錄JSON'])
                for platform in platforms:
                    for session in range(3):
                        for label, payload in [('normal','shirt'),('sqli',"' union select --"),('xss','<script>void(0)</script>')]:
                            sid = f'{split}-{platform}-{session}-{label}'
                            row = {'sample_id': sid, 'input': {'method':'GET','path':'/products',
                                'raw_query':f'q={payload}&nonce={sid}','raw_body':'','headers':{}},
                                'annotation':{'proposed_label':label}, 'metadata':{'platform':platform,
                                'split':split,'session_group':f'{split}-{platform}-{session}',
                                'http_executed':True,'request_input_version':3,'training_approved':False}}
                            writer.writerow([json.dumps(row)])
        output = tmp / 'original'
        from prepare_colab import package
        archive = tmp / 'colab.zip'
        package(data, archive)
        uploaded = tmp / 'Colab 中文路徑'; uploaded.mkdir()
        with zipfile.ZipFile(archive) as z:
            z.extractall(uploaded)
        command = [sys.executable,'-X','utf8','-B',str(uploaded/'model/train.py'),'--data-dir',str(uploaded/'data'),
                   '--output',str(output),'--allow-candidates','--trees','10']
        result = subprocess.run(command, cwd=tmp, capture_output=True, text=True, encoding='utf-8')
        test.assertEqual(result.returncode,0,result.stdout+result.stderr)
        for split in ('test','validation'):
            report=json.loads((output/split/'report.json').read_text(encoding='utf-8'))
            test.assertEqual(report['audit']['evaluated_split'],split)
            for key in ('macro_f1','weighted_f1','micro_f1','mcc','log_loss','multiclass_brier_score','majority_baseline'):
                test.assertIn(key,report)
            for name in ('metrics.csv','per-class.csv','curves.csv','confusion_matrix.csv','confusion_matrix_normalized.csv','predictions.csv','report.md'):
                test.assertTrue((output/split/name).is_file())
        moved=tmp/'中文 Ubuntu Windows'/'bundle';moved.mkdir(parents=True)
        with zipfile.ZipFile(output/'inference.zip') as z:
            z.extractall(moved)
        # Run only files in the relocated package from a different working directory.
        result=subprocess.run([sys.executable,'-X','utf8','-B',str(moved/'predict.py'),'--self-test'],
                              cwd=tmp,capture_output=True,text=True,encoding='utf-8')
        test.assertEqual(result.returncode,0,result.stdout+result.stderr)
        test.assertTrue(json.loads(result.stdout)['passed'])
        # Metadata edits are rejected before loading a mismatched model.
        (moved/'metadata.json').write_text('{}',encoding='utf-8')
        result=subprocess.run([sys.executable,'-X','utf8','-B',str(moved/'predict.py'),'--self-test'],
                              cwd=tmp,capture_output=True,text=True,encoding='utf-8')
        test.assertNotEqual(result.returncode,0)


class ExplicitTests(unittest.TestCase):
    def test_formal_accepts_traceable_http_without_manual_approval(self):
        from data_io import read_rows
        from request_input import from_evidence
        with tempfile.TemporaryDirectory(prefix='msdss-no-manual-review-unit-') as temp:
            root=Path(temp).resolve(); assert root.is_relative_to(Path(tempfile.gettempdir()).resolve())
            rows=[]
            for platform in ('bagisto','shopware'):
                record={'request_id':'unit-request','method':'GET','path':'/products','operation_path':'/products',
                        'request_target':'/products','raw_query':'','request_headers':{},
                        'request_body':None,'request_body_raw':'','status':200}
                relative=f'sentinel/dataset/evidence/{platform}-unit.json'
                file=root/relative;file.parent.mkdir(parents=True,exist_ok=True)
                file.write_text(json.dumps({'platform':platform,'requests':[record]}),encoding='utf-8')
                rows.append({'sample_id':platform,'input':from_evidence(record),'annotation':{'label':'normal'},
                    'metadata':{'platform':platform,'session_group':platform,'http_executed':True,
                        'request_input_version':3,'raw_target_captured':True,'raw_body_captured':True,
                        'source_evidence':relative,'source_evidence_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                        'request_id':'unit-request','http_status':200,'training_approved':False}})
            validate_rows(rows,'train',evidence_root=root)
            for row in rows:
                row['metadata'].pop('training_approved')
            validate_rows(rows,'train',evidence_root=root)
            # Legacy review decisions remain traceable but no longer control eligibility.
            legacy=root/'legacy.jsonl'
            legacy.write_text(''.join(json.dumps({'sample_id':r['sample_id'],'input':r['input'],'label':'normal',
                'audit':{'metadata':r['metadata'],'review_status':'rejected'}})+'\n' for r in rows),encoding='utf-8')
            imported=read_rows(legacy)
            validate_rows(imported,'train',evidence_root=root)
            self.assertTrue(all('training_approved' not in r['metadata'] for r in imported))

    def test_preflight_blocks_unexecuted_v2_without_training(self):
        # 直接檢查目前真實候選檔，不修改任何旗標或製造研究成績。
        data = HERE.parent / 'dataset/small-api-v2'
        result = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(HERE / 'train.py'), '--data-dir', str(data),
                                 '--check-only'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report['ready'])
        self.assertEqual(report['splits']['train']['rows'], 252)
        self.assertEqual(report['splits']['validation']['http_executed'], 0)
        self.assertTrue(any('未送出' in message for message in report['errors']))

    def test_malformed_credentials_are_redacted(self):
        for key in ('access_key','sessionId','pass\\u0077ord'):
            raw='{"'+key+'":"fixture-private-value",'
            self.assertNotIn('fixture-private-value',redact_body_text(raw,'application/json'))

    def test_formal_requires_explicit_http_and_source_evidence(self):
        rows=[{'input':{},'annotation':{'label':'normal'},'metadata':{'platform':p,'session_group':p,
            'training_approved':True,'request_input_version':3,'raw_target_captured':True,'raw_body_captured':True}}
            for p in ('bagisto','shopware')]
        with self.assertRaisesRegex(ValueError,'http_executed'):
            validate_rows(rows,'train')
        for row in rows: row['metadata']['http_executed']=True
        with self.assertRaisesRegex(ValueError,'evidence-root'):
            validate_rows(rows,'train')

    def test_family_and_source_groups_are_preserved(self):
        from train import groups
        rows=[{'input':{'path':'/'+str(i)},'metadata':{'payload':{'family':'same'}}} for i in range(2)]
        self.assertEqual(*groups(rows))

    def test_formal_rejects_faked_capture_flags(self):
        from data_io import check_evidence
        with tempfile.TemporaryDirectory(prefix='msdss-evidence-unit-') as temp:
            root=Path(temp).resolve(); assert root.is_relative_to(Path(tempfile.gettempdir()).resolve())
            file=root/'sentinel/dataset/evidence/report.json';file.parent.mkdir(parents=True)
            file.write_text(json.dumps({'platform':'bagisto','requests':[{'request_id':'r','status':200}]}),encoding='utf-8')
            row={'input':{},'metadata':{'platform':'bagisto','source_evidence':'sentinel/dataset/evidence/report.json',
                 'source_evidence_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'request_id':'r','http_status':200}}
            with self.assertRaisesRegex(ValueError,'原始'):
                check_evidence(row,root)


if __name__=='__main__':
    unittest.main()
