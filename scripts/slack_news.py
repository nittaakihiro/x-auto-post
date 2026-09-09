"""Slack delivery for reviewed news cards. No generation or X posting."""
import html
import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

LABELS = {'ai': 'AI最新ニュース', 'construction_ai': '建設AI', 'construction': '建設ニュース'}

def api(method, payload):
    req = urllib.request.Request('https://slack.com/api/' + method,
        data=json.dumps(payload).encode(), headers={'Authorization': 'Bearer ' + os.environ['SLACK_BOT_TOKEN'], 'Content-Type': 'application/json; charset=utf-8'})
    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.load(response)
    if not result.get('ok'):
        raise RuntimeError('Slack: ' + str(result.get('error')))
    return result

def send(text):
    dm = api('conversations.open', {'users': os.environ.get('SLACK_USER_ID', 'U01PHHAB887')})
    # plain_text blocks prevent source content from causing mentions or special markup.
    blocks = [{'type': 'section', 'text': {'type': 'plain_text', 'text': text[i:i+2900]}} for i in range(0, len(text), 2900)]
    return api('chat.postMessage', {'channel': dm['channel']['id'], 'text': text[:250], 'blocks': blocks[:50], 'unfurl_links': False, 'unfurl_media': False, 'parse': 'none'})

def render(card):
    action = {'original': '投稿', 'quote': '引用', 'reply': 'リプライ'}.get(card.get('action_type'), '候補')
    lines = [f"【{LABELS.get(card.get('pillar'), 'AIニュース')}／{action}】", card.get('text', '')]
    for key, label in [('target_post_url', '引用・リプ先'), ('source_url', '出典'), ('published_at', '発表日時'), ('checked_at', '確認日時'), ('why_now', '新情報'), ('availability', '利用条件'), ('construction_use', '建設での使い方'), ('caveat', '確認事項'), ('media_url', '公式デモ・添付候補')]:
        if card.get(key):
            lines.append(label + ': ' + str(card[key]))
    return '\n\n'.join(lines)

def main():
    dashboard = json.loads(Path('output/dashboard.json').read_text())
    today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    if dashboard.get('version') != 5 or dashboard.get('date') != today:
        print('No current v5 dashboard; old cards are not re-sent.')
        return
    cards = dashboard.get('news_cards', [])
    if not cards:
        print('No new reviewed cards.')
        return
    for card in cards[:2]:
        if not card.get('text') or not card.get('source_url'):
            raise ValueError('Missing reviewed text or source_url')
    for card in cards[:2]:
        send(render(card))
    print(f'Sent {min(len(cards), 2)} reviewed cards.')

if __name__ == '__main__':
    main()
