import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import make_post_image

class MediaSkipTests(unittest.TestCase):
    def test_none_and_video_do_not_generate_or_send(self):
        for extra in ({'image': {'type': 'none'}}, {'image': {'type': 'gemini'}, 'video_url': 'https://example.com/demo'}):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as directory:
                queue = Path(directory) / 'queue.json'
                queue.write_text(json.dumps([dict(id='test', date='2026-09-10', status='draft', **extra)]))
                with patch.object(make_post_image, 'QUEUE', queue), patch.object(sys, 'argv', ['make_post_image', '--post-id', 'test']), patch.object(make_post_image, 'gen_gemini') as generate, patch.object(make_post_image, 'gen_screenshot') as screenshot:
                    self.assertEqual(make_post_image.main(), 0)
                    generate.assert_not_called()
                    screenshot.assert_not_called()
