import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import unittest
from datetime import datetime, timezone, timedelta
from collect_ai_news import parse, merge
from slack_news import render

SOURCE = {'name': 'Official', 'pillar': 'ai'}
NOW = datetime(2026, 9, 9, 0, tzinfo=timezone.utc)

def item(id='new', age=1):
    return {'id': id, 'title': 'New model', 'url': 'https://example.com/'+id, 'source': 'Official', 'published_at': (NOW-timedelta(hours=age)).isoformat(), 'pillar': 'ai'}

class NewsTests(unittest.TestCase):
    def test_first_run_seeds_without_mass_notification(self):
        state=merge({}, [(SOURCE,[item()],None)],NOW)
        self.assertEqual(state['items'][0]['notify_status'], 'seeded')
    def test_new_item_notified_once_and_failure_retains_outbox(self):
        state=merge({},[(SOURCE,[item('old')],None)],NOW)
        state=merge(state,[(SOURCE,[item('old'),item()],None)],NOW)
        self.assertEqual(len([i for i in state['items'] if i['notify_status']=='pending']),1)
        failed=merge(state,[(SOURCE,[],'timeout')],NOW)
        self.assertEqual(len(failed['items']),2)
        for i in state['items']: i['notify_status']='sent'
        again=merge(state,[(SOURCE,[item('old'),item()],None)],NOW)
        self.assertFalse(any(i['notify_status']=='pending' for i in again['items']))
    def test_old_future_and_undated_are_not_breaking_news(self):
        undated={**item('unknown'), 'published_at':None}
        state=merge({'initialized_sources':['Official']},[(SOURCE,[item('old',48), item('future',-1),undated],None)],NOW)
        self.assertTrue(all(i['notify_status']=='old_or_undated' for i in state['items']))
    def test_rss_atom_and_unsafe_links(self):
        rss=b'<rss><channel><item><title>test</title><link>https://example.com/a#fragment</link><pubDate>Wed, 09 Sep 2026 00:00:00 GMT</pubDate></item><item><title>bad</title><link>javascript:alert(1)</link></item></channel></rss>'
        result=parse(rss,SOURCE);self.assertEqual(len(result),1);self.assertEqual(result[0]['url'],'https://example.com/a')
        atom=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>demo</title><link href="https://example.com/b"/><updated>2026-09-09T00:00:00Z</updated></entry></feed>'
        self.assertEqual(parse(atom,SOURCE)[0]['published_at'],'2026-09-09T00:00:00+00:00')
    def test_slack_card_has_completed_text_and_source(self):
        rendered=render({'pillar':'construction_ai','action_type':'quote','text':'完成文','source_url':'https://example.com','target_post_url':'https://x.com/test/status/1','availability':'予告のみ'})
        for expected in ['建設AI','引用','完成文','https://example.com','予告のみ']: self.assertIn(expected,rendered)

if __name__=='__main__':unittest.main()
