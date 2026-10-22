import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('activity',Path(__file__).parents[1]/'clients/codex_activity.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
NOW=1792700000
class ActivityTests(unittest.TestCase):
 def test_lifecycle_and_expiry_preserve_unknown(self):
  from datetime import datetime,timezone
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'session.jsonl'
   def put(kind,age=0):
    path.write_text(json.dumps({'timestamp':datetime.fromtimestamp(NOW,timezone.utc).isoformat(),'type':'event_msg','payload':{'type':kind,'private_prompt':'never export'}})+'\n');os.utime(path,(NOW-age,NOW-age))
   self.assertEqual(module.observe_activity(d,NOW)['state'],'unknown')
   for kind,state in [('task_started','working'),('task_complete','idle'),('turn_aborted','idle'),('task_failed','error')]:
    put(kind);value=module.observe_activity(d,NOW);self.assertEqual(value['state'],state);self.assertNotIn('private_prompt',json.dumps(value));self.assertEqual(set(value),{'source','state','observed_at','expires_at'})
   put('task_started',91);self.assertEqual(module.observe_activity(d,NOW)['state'],'unknown')
 def test_noise_does_not_create_work(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'s.jsonl';p.write_text('{broken}\n'+json.dumps({'type':'event_msg','timestamp':'2026-10-22T15:00:00Z','payload':{'type':'token_count'}}));os.utime(p,(NOW,NOW))
   self.assertEqual(module.observe_activity(d,NOW)['state'],'unknown')
