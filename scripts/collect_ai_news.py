"""Free primary-source RSS/Atom collector. Candidates, never verified post drafts.
Initial fetch seeds history silently. New entries are an outbox until Slack succeeds.
"""
import argparse
import hashlib
import json
import os
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent

def canonical(url):
    parts = urlsplit(url)
    if parts.scheme not in ('https', 'http') or not parts.netloc:
        return None
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip('/'), parts.query, ''))

def parse(data, source):
    root = ET.fromstring(data)
    output = []
    for node in list(root.findall('.//item')) + list(root.findall('{http://www.w3.org/2005/Atom}entry')):
        def val(name):
            found = node.find(name)
            if found is None:
                found = node.find('{http://www.w3.org/2005/Atom}' + name)
            return (''.join(found.itertext()).strip() if found is not None else '')
        url = val('link')
        if not url:
            for link in node.findall('{http://www.w3.org/2005/Atom}link'):
                if link.get('rel', 'alternate') == 'alternate':
                    url = link.get('href', '')
                    break
        url = canonical(url)
        if not url or not val('title'):
            continue
        date = val('pubDate') or val('published') or val('updated')
        try:
            try:
                published = parsedate_to_datetime(date)
            except (ValueError, TypeError):
                published = datetime.fromisoformat(date.replace('Z', '+00:00'))
            if published.tzinfo is None:
                raise ValueError('No timezone')
            date = published.astimezone(timezone.utc).isoformat()
        except (ValueError, TypeError, OverflowError):
            date = None
        output.append({'id': hashlib.sha256(url.encode()).hexdigest()[:24], 'title': val('title')[:400], 'url': url, 'source': source['name'], 'pillar': source['pillar'], 'published_at': date})
    if not output:
        raise ValueError('No RSS/Atom entries')
    return output

def fetch(source):
    try:
        req = urllib.request.Request(source['url'], headers={'User-Agent': 'NITACO-AI-News/1.0 (+https://github.com/nittaakihiro/x-auto-post)'})
        with urllib.request.urlopen(req, timeout=20) as response:
            data = response.read(4_000_001)
        if len(data) > 4_000_000:
            raise ValueError('Feed too large')
        return source, parse(data, source), None
    except Exception as error:
        return source, [], type(error).__name__ + ': ' + str(error)[:160]

def merge(state, results, now):
    entries = {x['id']: x for x in state.get('items', [])}
    health = []
    known_sources = set(state.get('initialized_sources', []))
    for source, items, error in results:
        health.append({'source': source['name'], 'ok': error is None, 'error': error})
        if error:
            continue
        seed = source['name'] not in known_sources
        for item in items:
            if item['id'] in entries:
                continue
            date = datetime.fromisoformat(item['published_at']) if item['published_at'] else None
            fresh = date is not None and timedelta(0) <= now - date <= timedelta(hours=24)
            entries[item['id']] = {**item, 'first_seen_at': now.isoformat(), 'notify_status': 'seeded' if seed else ('pending' if fresh else 'old_or_undated')}
        known_sources.add(source['name'])
    # Keep recent discovery history, including silent initial seeds, to deduplicate.
    values = sorted(entries.values(), key=lambda x: x['first_seen_at'], reverse=True)[:3000]
    return {'checked_at': now.isoformat(), 'initialized_sources': sorted(known_sources), 'health': health, 'items': values}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--notify', action='store_true')
    parser.add_argument('--output', default=str(ROOT / 'output/ai_news.json'))
    args = parser.parse_args()
    path = Path(args.output)
    state = json.loads(path.read_text()) if path.exists() else {}
    sources = json.loads((ROOT / 'config/ai_sources.json').read_text())
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch, sources))
    now = datetime.now(timezone.utc)
    updated = merge(state, results, now)
    if args.notify:
        from slack_news import send
        if all(not h['ok'] for h in updated['health']):
            previous = state.get('last_failure_alert_at')
            if not previous or now - datetime.fromisoformat(previous) > timedelta(hours=12):
                send('AIニュース収集：全フィードを取得できませんでした。自動収集ログの確認が必要です。')
                updated['last_failure_alert_at'] = now.isoformat()
            else:
                updated['last_failure_alert_at'] = previous
        pending = [x for x in updated['items'] if x['notify_status'] == 'pending']
        for item in pending:
            if now - datetime.fromisoformat(item['published_at']) > timedelta(hours=24):
                item['notify_status'] = 'expired'
        pending = [x for x in pending if x['notify_status'] == 'pending'][:5]
        if pending:
            text = '海外AI：新着候補（原文未検証／日本語の投稿案は朝・昼・夜に作成）\n\n' + '\n\n'.join(f"{x['source']}｜{x['title']}\n発表: {x['published_at']}\n{x['url']}" for x in pending)
            send(text)
            for item in pending:
                item['notify_status'] = 'sent'
                item['notified_at'] = now.isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)
    print(json.dumps({'health': updated['health'], 'items': len(updated['items'])}, ensure_ascii=False))
    if all(not h['ok'] for h in updated['health']):
        raise SystemExit(1)

if __name__ == '__main__':
    main()
