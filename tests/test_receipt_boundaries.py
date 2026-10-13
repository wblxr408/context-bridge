import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'context-bridge/scripts'))
import requirements

class ReceiptBoundaries(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT);self.root=Path(self.tmp.name)
        (self.root/'request.md').write_text('按照最新要求继续。',encoding='utf-8')
        self.ledger={'schema':1,'task_id':'task','snapshot_id':'task/revision-2','requirements':[{'id':'R001','revision':2,'status':'active','kind':'goal','scope':'global','always_load':True,'statement':'按照最新要求继续。','source':{'path':'request.md','quote':'按照最新要求继续。','locator':'用户原文'},'acceptance':'尊重最新版本','progress':'pending','evidence':[]}]}
        self.proof={'task_id':'task','snapshot_id':'task/revision-2','scope':'global','checks':[{'id':'R001','revision':2,'result':'aligned','interpretation':'依据用户最新要求','next_action':'继续任务'}]}
        self.save()
    def save(self):
        (self.root/'requirements.json').write_text(json.dumps(self.ledger,ensure_ascii=False),encoding='utf-8')
        (self.root/'proof.json').write_text(json.dumps(self.proof,ensure_ascii=False),encoding='utf-8')
    def tearDown(self):self.tmp.cleanup()
    def receipt(self):return requirements.receipt(self.root,'global',self.root/'proof.json',self.ledger['snapshot_id'])
    def test_snapshot_identity_cannot_bind_different_task_namespace(self):
        self.ledger['snapshot_id']=self.proof['snapshot_id']='other-task/revision-2';self.save()
        with self.assertRaises(ValueError):self.receipt()
    def test_old_revision_and_unknown_alignment_are_rejected(self):
        self.proof['checks'][0]['revision']=1;self.save()
        with self.assertRaises(ValueError):self.receipt()
        self.proof['checks'][0].update(revision=2,result='unknown');self.save()
        with self.assertRaises(ValueError):self.receipt()
    def test_missing_and_duplicate_requirement_receipts_are_rejected(self):
        row=self.proof['checks'][0];self.proof['checks']=[];self.save()
        with self.assertRaises(ValueError):self.receipt()
        self.proof['checks']=[row,row];self.save()
        with self.assertRaises(ValueError):self.receipt()
    def test_changed_requirement_without_revision_bump_is_rejected(self):
        old=self.root/'previous';old.mkdir()
        (old/'request.md').write_text('按照最新要求继续。',encoding='utf-8');(old/'requirements.json').write_text(json.dumps(self.ledger,ensure_ascii=False),encoding='utf-8')
        self.ledger['requirements'][0]['acceptance']='不同的业务目标';self.save()
        with self.assertRaises(ValueError):requirements.check(self.root,old)
