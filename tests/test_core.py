import json
import os
import unittest
from unittest.mock import patch
from autopilot.core import config,collect_news,decode_marker,encode_marker,validate_draft,draft,research

RSS=b'''<rss><channel>
<item><title>How AI apps change daily work</title><link>https://news.google.com/rss/articles/a</link></item>
<item><title>Evaluating popular workflow tools</title><link>https://news.google.com/rss/articles/b</link></item>
<item><title>Software skills in the workplace</title><link>https://news.google.com/rss/articles/c</link></item>
</channel></rss>'''

def fake_model(url,payload):
    prompt=payload['contents'][0]['parts'][0]['text']
    if 'niche researcher' in prompt:
        data={'ranked':[{'id':'ai_workflows','why':'interest hypothesis',
              'original_angle':'original evaluation checklist',
              'monetization':'possible referrals','risks':'verify accuracy'}]}
    else:
        data={'title':'Evaluate a useful software tool before choosing',
              'description':'Original evaluation framework with sources.',
              'scenes':[{'headline':'Consider the actual outcome',
                'narration':'A useful tool should solve a recurring problem without introducing extra manual work. Compare it fairly against your existing process. Check assumptions before making any purchase.',
                'visual_note':'Evidence checklist'} for _ in range(8)],
              'source_urls':['https://news.google.com/rss/articles/a',
                             'https://news.google.com/rss/articles/b'],
              'tags':['productivity'],'risk_notes':'Check factual assumptions'}
    return {'candidates':[{'content':{'parts':[{'text':json.dumps(data)}]}}]}

class TestAutopilot(unittest.TestCase):
    def test_free_safety(self):
        self.assertEqual(config()['budget_usd'],0)
        self.assertIs(config()['paid_fallbacks'],False)
        self.assertEqual(config()['approval_mode'],'each')
    def test_feed(self):
        self.assertEqual(len(collect_news('tools',opener=lambda _:RSS)),3)
    def test_research(self):
        self.assertEqual(research(request_fn=fake_model,fetcher=lambda _:RSS)[0]['id'],
                         'ai_workflows')
    def test_long_video(self):
        d=draft({'id':'ai_workflows','name':'AI','query':'apps'},
                'long',request_fn=fake_model,fetcher=lambda _:RSS)
        self.assertEqual(len(d['scenes']),8)
        self.assertEqual(d['format'],'long')
    def test_fabricated_sources_rejected(self):
        with self.assertRaises(ValueError):
            validate_draft({'title':'Proper length original video title',
                            'source_urls':['https://fake.example'],'scenes':[]},
                           [],{'id':'ai_workflows'},'short')
    def test_marker(self):
        obj={'run_id':123,'draft_id':'abc','sha256':'sample'}
        self.assertEqual(obj,decode_marker(encode_marker('DRAFT',obj),'DRAFT'))
    def test_no_key_no_money(self):
        from autopilot.core import gemini_json
        with patch.dict(os.environ,{'GEMINI_API_KEY':''}):
            with self.assertRaisesRegex(RuntimeError,'No paid fallback'):
                gemini_json('hello')
    def test_only_owner(self):
        from autopilot.cli import verify_owner_event
        event={'action':'labeled','label':{'name':'publish-approved'},
               'sender':{'login':'stranger'},
               'issue':{'user':{'login':'github-actions[bot]'}}}
        with patch.dict(os.environ,{'GITHUB_REPOSITORY':'Mrperkins/free-content-autopilot'}):
            with self.assertRaisesRegex(RuntimeError,'owner'):
                verify_owner_event(event,'publish-approved')
    def test_only_bot_created_issues(self):
        from autopilot.cli import verify_owner_event
        event={'action':'labeled','label':{'name':'publish-approved'},
               'sender':{'login':'Mrperkins'},
               'issue':{'user':{'login':'stranger'}}}
        with patch.dict(os.environ,{'GITHUB_REPOSITORY':'Mrperkins/free-content-autopilot'}):
            with self.assertRaisesRegex(RuntimeError,'generated'):
                verify_owner_event(event,'publish-approved')

if __name__=='__main__': unittest.main()
