"""Offline regression checks using actual Tweepy response objects."""
import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import unittest
import tweepy

tree=ast.parse((Path(__file__).resolve().parents[1] / 'scripts' / 'x_poster.py').read_text())
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='XPoster')
method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='get_my_tweets')
namespace={}
exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),'get_my_tweets','exec'),namespace)

class LongPostTests(unittest.TestCase):
    def fetch(self,**extra):
        data={'id':'1','edit_history_tweet_ids':['1'],'text':'冒頭の文章。','created_at':'2026-09-04T11:38:44.000Z','public_metrics':{'impression_count':180},'referenced_tweets':[],**extra}
        client=Mock();client.get_users_tweets.return_value=SimpleNamespace(data=[tweepy.Tweet(data)])
        out=namespace['get_my_tweets'](SimpleNamespace(client=client,user_id='100'),100,True)
        self.assertIn('note_tweet',client.get_users_tweets.call_args.kwargs['tweet_fields'])
        return out[0]
    def test_long_text_is_not_misclassified_as_cut(self):
        full='冒頭の文章。\n'+('本文と現場への含意が続いている。'*25)
        t=self.fetch(note_tweet={'text':full})
        self.assertEqual(t['text'],full)
        self.assertEqual(t['text_preview'],'冒頭の文章。')
        self.assertEqual(t['text_source'],'note_tweet')
    def test_standard_post(self):
        t=self.fetch();self.assertEqual(t['text'],'冒頭の文章。');self.assertEqual(t['text_source'],'text')
    def test_missing_note_text_does_not_drop_preview(self):
        for v in [None,{}, {'text':''}]:self.assertEqual(self.fetch(note_tweet=v)['text'],'冒頭の文章。')
    def test_external_reply_and_quote_classification_preserved(self):
        t=self.fetch(in_reply_to_user_id='200',referenced_tweets=[{'type':'quoted','id':'3'}])
        self.assertTrue(t['is_reply']);self.assertTrue(t['is_quote'])
    def test_self_reply_not_counted_as_external(self):
        self.assertFalse(self.fetch(in_reply_to_user_id='100')['is_reply'])

if __name__=='__main__':unittest.main()
