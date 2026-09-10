import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from validate_editorial import validate, FIELDS

class EditorialTests(unittest.TestCase):
    def setUp(self):
        e = {k: 'checked' for k in FIELDS}
        e.update(scores={str(i): 2 for i in range(5)}, source_url='https://example.com/release', unverified=[])
        self.p = dict(date='2026-09-10', time='12:00', text='投稿本文', status='draft', editorial=e)
        self.d = dict(version=6, date=self.p['date'], generated_at='2026-09-10T11:00:00+09:00', slot='noon', original_post=copy.deepcopy(self.p), engage_cards=[])
    def test_valid_handoff(self):
        self.assertEqual(validate(self.d, [self.p]), [])
    def test_prevent_automatic_post(self):
        self.p['status'] = 'pending'
        self.assertTrue(validate(self.d, [self.p]))
    def test_reject_wrong_slot_text(self):
        self.d['original_post']['text'] = '前の枠'
        self.assertTrue(validate(self.d, [self.p]))
    def test_skip_cannot_resend_old_draft(self):
        self.d.update(original_post=None, skip_reason='採用なし')
        self.assertTrue(validate(self.d, [self.p]))
        self.assertEqual(validate(self.d, []), [])
    def test_reject_missing_evidence(self):
        self.p['editorial']['source_url'] = ''
        self.d['original_post']['editorial']['source_url'] = ''
        self.assertTrue(validate(self.d, [self.p]))

if __name__ == '__main__':
    unittest.main()
