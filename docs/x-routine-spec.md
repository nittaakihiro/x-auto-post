# ルーティン共通仕様 v5（x-post-morning / noon / evening）

戦略・型・文体・NG表現の正本は `docs/x-strategist.md`（v5 チャエン型）。この文書は**3ルーティン共通の手順**だけを持つ。矛盾したら x-strategist.md が勝つ。旧版は `docs/archive/`。

## 0. 運転モード

- 成果物は**下書き**（`status='draft'`）。自動投稿は走らない。新田さんは「画像を付けて投稿→■補足を自己リプ」だけ
- **下書きは完成文**。v4.1のリライト前提（一人称なし・hint付き）は廃止。チャエン型は主語なし・です・ます基調なので、そのまま投稿できる文にする。`hint` は渡さなくてよい
- 各枠1本。休載は鮮度48h以内のネタが本当にゼロの時だけ（判定前に5ネタ探索）

## 1. 枠ごとの柱

| ルーティン | 枠 | 柱 | ネタの取り方 |
|:--|:--|:--|:--|
| morning（6:30 JST） | 07:25 | ① AI速報 | `news_feed.json` の ai_global を新しい順に見る → `ai_buzz.json` の海外アカウント → WebSearch。**土曜は週間まとめ**（§5） |
| noon（11:00 JST） | 12:00 | ② AI×建設 | `news_feed.json` の construction_* で `ai_related=true` ＋ ai_global/ai_japan から建設に直結するもの（CAD/BIM/ロボ/現場/不動産/設計）→ `slack_buzz.json` → WebSearch（建設 AI／ゼネコン 生成AI／construction AI） |
| evening（19:00 JST） | 20:00 | ③ 建設ニュース | AI絡み優先（`news_feed.json` construction_* → `slack_buzz.json`）。無ければ `slack_buzz.json`／`ai_buzz.json` のバズ投稿を引用RT（`post_type='quote_rt'`＋`quote_tweet_id`）。それも無ければ型パクリ（バズ投稿の構成を借りて建設の中身に） |

当日の他枠と同じニュース・同じ【タグ】を使わない。

## 2. 必須ゲート（1つでも欠けたら別ネタ・最大3回試行）

1. **鮮度**: AIニュース48h以内（24h優先）／建設72h以内
2. **固有名詞1つ以上**（企業・製品・人物・機関）
3. **数字1つ以上**（箇条書きの中に。地の文は0〜1個）
4. **新情報**: news_feed／buzz／WebSearchで裏取りできる一次ソースがある。裏取り不能な要素は削る
5. **建設への含意1〜2行**（柱①②必須。柱③は「AIで言うと」の1行）
6. **画像指定**: `article_url`（スクショ元）を必ず渡す。表・比較が作れる時だけ `image_type='gemini'`＋`image_prompt` を追加
7. **■補足**: `reply_text` に「■ 補足」（背景1〜3行）＋「■ 出典」（URL1〜2本）を渡す。本文にURLは置かない

## 3. 型と文体（x-strategist.md の「投稿の型」「文体」に従う）

```
【速報】固有名詞＋何が起きたか

本音1行

・事実1（数字）
・事実2
・事実3

建設への含意1〜2行
```

- 段落ごとに空行。100〜200字（引用RTは60〜120字）。【タグ】は7種（速報／朗報／検証／注目／警鐘／驚愕／必見）を3割程度で
- です・ます基調＋ゆるい語尾（。。／笑／〜な気がする）。絵文字なし。攻撃・極論なし。ハッシュタグなし。「地味に〜」禁止（絡みカードも同じ）
- 一人称は書かなくてよい。書くなら「僕」

## 4. 手順（毎枠共通）

1. `cat output/news_feed.json | python3 -c "import json,sys;d=json.load(sys.stdin);[print(i['published_jst'],i['category'],i['ai_related'],i['source'],'|',i['title'],'|',i['url']) for i in d['items'][:80]]"` で48h分を眺める
2. `cat output/ai_buzz.json` と `cat output/slack_buzz.json`（X側のバズ）
3. 候補を5本並べ、柱・鮮度・「1行目で止まるか」で1本選ぶ。チャエン（@masahirochaen）が既に出したネタは、彼より早いか建設の角度がある時だけ
4. WebFetch で一次ソースを開いて裏取り（数字・日付・固有名詞）
5. 本文（型どおり）＋ `reply_text`（■補足／■出典）＋ `article_url` を作る
6. マンネリチェック（§6）→ セルフチェック（§8）
7. `add_post`（§9）→ 絡みカード（§7）→ commit+push（§10）

## 5. 土曜朝は週間まとめ（morning のみ・DOW_JST=6）

```
【🔥今週の建設×AIニュース】

今週は〇〇が一番の話題でした。

① 固有名詞: 1行
② 固有名詞: 1行
③ 固有名詞: 1行
④ 固有名詞: 1行
⑤ 固有名詞: 1行

一言（来週の見どころ or 建設への含意）
```
- 月〜金の news_feed／過去6日のpost_queueから5本。AI 3本＋建設×AI 2本が目安。各1行30字以内
- `reply_text` に5本の出典URLを「■ 出典」で並べる。画像は表（`image_type='gemini'`）でもよい

## 6. マンネリチェック

```bash
python3 -c "
import json
from datetime import datetime,timezone,timedelta
JST=timezone(timedelta(hours=9)); cutoff=(datetime.now(JST)-timedelta(days=14)).strftime('%Y-%m-%d')
posts=[p for p in json.load(open('output/post_queue.json')) if p.get('date','')>=cutoff and p.get('type') in ('original','quote_rt')]
print(chr(10).join(p.get('date','')+' '+p.get('time','')+' '+p.get('text','')[:120].replace(chr(10),'/') for p in posts[-30:]))"
```
- 同一ニュース（同URL・同一の固有名詞×数字）は14日間ban
- 同じ【タグ】を3投稿連続で使わない。書き出しは直近5投稿と変える

## 7. 絡みカード（各枠3〜4枚・完成文・1日10枚目安）

- 朝・昼＝リプ型3〜4枚。夜＝リプ型＋**引用翻訳型を最低1枚**（海外AIアカウントのバズ投稿を日本語要約＋本音1行。「＞」で要約を示す）
- 相手: 国内AI（@masahirochaen 最優先 / @shi3z @kajikent @ochyai @ai_database）＋建設A tier（@karube_sanei @inatake0 @TKG_CraftBank @Stoneman_ISHIO @shinkojuki @carpentershoyan @monozukuritarou @sekokan_kun）＋海外AI（引用翻訳型のみ）
- 3条件AND（機械検証）: 24h以内（snowflake検証・6h優先）／AIか建設に関連／いいね50+ or フォロワー2,000+
  ```bash
  python3 -c "print(__import__('datetime').datetime.fromtimestamp(((ID>>22)+1288834974657)/1000))"
  ```
- リプはデータ補足＞一次情報＞共感。60〜100字・です・ます。「いいですね」だけは没。DM誘導・自社宣伝なし
- 同日の他枠と同じ相手・同じ投稿は選ばない。条件未達で無理に埋めない
- 書き込み先: `dashboard.json` の `engage_cards`（その枠の3〜4枚・上書きOK）と `engage_pool_{枠}`。フィールド: `no, action_type("reply"|"quote"), target_account, name, tier, target_post_url, target_snippet, engagement, text`

## 8. セルフチェック（生成後に必ず）

- [ ] 1行目だけで何のニュースか分かる（【タグ】or 固有名詞で始まる）
- [ ] 段落ごとに空行／100〜200字／箇条書き3〜5点／数字は箇条書きに
- [ ] です・ます基調・本音1行あり・絵文字なし・ハッシュタグなし・本文URLなし
- [ ] 建設への含意1〜2行（柱①②）
- [ ] `article_url` あり／`reply_text` に ■補足＋■出典 あり
- [ ] 一次ソースで裏取り済み（数字・日付・固有名詞）／創作なし
- [ ] `status='draft'`／当日の他枠と重複なし／14日banなし
- [ ] 絡みカード3〜4枚が完成文

## 9. キュー書き込み

```bash
pip install python-dotenv
```
```python
import sys
sys.path.insert(0, 'scripts')
from post_queue import load_queue, add_post
q = load_queue()
q = add_post(q, today, '07:25', '本文（型どおり・空行あり）', freshness='locked',
             status='draft',
             reply_text='■ 補足\n背景1〜3行\n\n■ 出典\nhttps://...',
             article_url='https://...（スクショ元・見出しが無料で見えるページ）',
             image_type='screenshot')
# 引用RTの時: post_type='quote_rt', quote_tweet_id='<ツイートID>'（本文60〜120字）
# 表画像を付ける時だけ: image_type='gemini', image_prompt='...'
```

枠と freshness: 朝 `07:25`/`locked`、昼 `12:00`/`updatable`、夕 `20:00`/`updatable`。

## 10. commit & push

```bash
git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"
git config --global --unset-all http.https://github.com/.extraheader 2>/dev/null || true
git config --unset-all http.https://github.com/.extraheader 2>/dev/null || true
git pull --rebase --autostash origin main || true
git add output/post_queue.json output/dashboard.json
git commit -m "draft: <日付> <枠>（休載時は skip: <枠> <理由>）"
git -c http.https://github.com/.extraheader= push https://$PAT@github.com/nittaakihiro/x-auto-post.git HEAD:main
```

PATはルーティンのプロンプト内に埋め込む（**リポ内ファイルには絶対に書かない**。2026-07-11に実際に失効させた事故あり）。
