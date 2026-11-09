"""用真正Git入庫／checkout檢查檔案bytes，不以工作目錄測試代替發布檢查。"""
import csv
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from data_io import read_rows
from preflight import inspect_dataset
from train import groups
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'sentinel/dataset/small-api-v6'


class GitArtifactBytesTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('git'),'此測試需要Git')
    def test_git_blob_and_checkout_preserve_mixed_newlines(self):
        # 同時包含CSV記錄CRLF與儲存格中的真正CRLF/LF，不能對整份CSV正規化。
        text=io.StringIO(newline='');writer=csv.writer(text)
        writer.writerow(['raw_body','raw_query']);writer.writerow(['line1\r\nline2\nline3','q=%0D%0A'])
        payload=text.getvalue().encode('utf-8-sig')
        files={'sentinel/dataset/small-api-v6/train.csv':payload,
               'sentinel/dataset/reference/normal-candidates.csv':payload,
               'sentinel/model/SKELETON-PYTHON-LICENSE.txt':b'License\r\nparagraph\n',
               'sentinel/model/_skeleton_html_v1.py':b'# frozen\r\n'}
        for autocrlf in ('true','false'):
            with self.subTest(autocrlf=autocrlf),tempfile.TemporaryDirectory(prefix='msdss-git-bytes-') as tmp:
                tmp=Path(tmp).resolve();self.assertTrue(tmp.is_relative_to(Path(tempfile.gettempdir()).resolve()))
                repo=tmp/'repo';repo.mkdir();destination=tmp/'checkout';destination.mkdir()
                def git(*args):
                    return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE)
                git('init','--quiet');git('config','core.autocrlf',autocrlf)
                (repo/'.gitattributes').write_bytes((ROOT/'.gitattributes').read_bytes())
                for name,value in files.items():
                    path=repo/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(value)
                git('add','--all')
                for name,value in files.items():self.assertEqual(git('show',':'+name),value,name)
                git('checkout-index','--all','--prefix='+destination.as_posix()+'/')
                for name,value in files.items():self.assertEqual((destination/name).read_bytes(),value,name)

    def test_real_csv_conversion_is_still_rejected(self):
        # 修正Git行為，不放寬真正資料的完整性；編輯器換行改寫仍應被發現。
        with tempfile.TemporaryDirectory(prefix='msdss-eol-tamper-') as tmp:
            tmp=Path(tmp).resolve();self.assertTrue(tmp.is_relative_to(Path(tempfile.gettempdir()).resolve()))
            for name in ['train.csv','test.csv','validation.csv','challenge.csv','skeleton-catalog.csv','provenance.json']:
                shutil.copy2(DATA/name,tmp/name)
            path=tmp/'test.csv';original=path.read_bytes();self.assertIn(b'\r\n',original)
            path.write_bytes(original.replace(b'\r\n',b'\n'))
            _,_,_,_,report=inspect_dataset(tmp,groups,offline=True)
            self.assertFalse(report['ready'])
            self.assertTrue(any('保留集與凍結指紋不符' in e for e in report['errors']),report['errors'])


if __name__=='__main__':unittest.main()
