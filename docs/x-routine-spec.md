# ルーティン共通仕様（x-post-morning / noon / evening）

戦略・文体・NG表現の正本は `docs/x-strategist.md`。この文書は**3ルーティン共通の手順仕様**だけを持つ。矛盾したら x-strategist.md が勝つ。

2026-07-27 新設。ルーティンのプロンプトが肥大して更新しづらくなったため、共通部分をここへ集約した。

---

## 1. 投稿の必須要素ゲート（1つでも欠けたら没にして別ネタ・最大3回試行）

1. **実名1つ以上**（企業名 / 制度名 / 省庁名 / 統計名。出典が言える実データ）
2. **数字2つ以上**（%・円・件数・人数・日付）
3. **新情報1つ以上**（読者がブックマークか引用したくなる）
4. **現場への含意1行**（格言・標語ではなく具体で）
5. **一人称の一次観点を1文以上**（v3.2で追加・転換の要）

### ゲート5の根拠と書き方（最重要・ここを外すと数字が出てもフォローされない）

4/29〜7/27の417投稿CSV実測: フォローが付いたのは11本のみで、**その全てが一人称の一次観点を持っていた**（imp 46〜334と小さい）。一方、直近の高imp投稿（鹿島3兆円 / サンゲツ値上げ / 札幌再開発）は**全てフォロー0**。事実の要約だけではニュースbotと区別がつかず、フォローする理由が生まれない。

- ○ 「僕は〜と思ってる」「〜が気になった」「〜だと見てる」を**地の文で**書く
- ○ 構成は 事実 → **僕の解釈** → 現場への含意 の順で1本にまとめる
- ✕ 創作した商談・訪問・会話（**実際に起きたことだけ**。v3の創作全廃は維持）
- ✕ 伝聞ヘッジ（「〜と言われている」「〜が指摘されている」）で当事者性を消す
- ✕ 誰でも言えるコンサル一般論（「大事なのは運用だ」等）に着地する
- エピソードバンクの表は創作を含むため**本文使用禁止**。ネタが無ければ無理に体験を作らず、事実＋自分の解釈でゲート5を満たす

## 2. 自己リプは作らない（v3.2）

`add_post` に `reply_text` を**渡さない**。ソースURLリプも廃止。

- 実測: ソースリプ42本でimp中央38・プロフ訪問合計1。投稿の46%を占めながら何も生まず、アカウント全体のリンク比率を上げてリーチを削っていた（リンク有りimp中央50 vs リンク無し183）
- **出典は本文内に「機関名＋発表日」で書く**（例:「厚生労働省が5月27日に公表した確定値では」）。URLは本文にもリプにも載せない

## 3. マンネリチェック v3（ジャンルbanは廃止済み）

過去14日の post_queue.json のオリジナル投稿を読んで、(1)同一の具体的数字×固有名詞ペアの再利用禁止（ジャンル自体は新事実が出れば毎週OK） (2)直近5投稿と同じ書き出し構文禁止、の2つだけ守る。

```bash
python3 -c "
import json
from datetime import datetime,timezone,timedelta
JST=timezone(timedelta(hours=9)); cutoff=(datetime.now(JST)-timedelta(days=14)).strftime('%Y-%m-%d')
posts=[p for p in json.load(open('output/post_queue.json')) if p.get('date','')>=cutoff and p.get('type')=='original']
print(chr(10).join(p.get('date','')+' '+p.get('text','') for p in posts[-25:]))"
```

## 4. ネタ収集

WebSearchで収集。鉄板ジャンル: 資材供給・値上げ / ゼネコン・住設の決算と再編 / 制度改正＋施行日・締切 / 労務単価・賃金・人手 / 倒産・資金繰りの構造 / 建設テック動向。

ニュースは72h以内優先、統計は発表6ヶ月以内のみ。**ファクトチェック必須**: 企業名・数字・制度名・日付はWebSearchで裏取りし、裏取り不能な要素は削るか没にする。

## 5. セルフチェック（生成後に必ず実行）

- [ ] ゲート5項目すべて（特に**5の一人称**。無ければ書き足すか没）
- [ ] 100〜300字（朝枠は250〜300推奨 / 夕枠C型は90字台可）
- [ ] 空行ゼロ・文ごと改行済み（本文3行以上）
- [ ] **URLが本文に入っていない / reply_text を渡していない**
- [ ] AI臭ワード2未満（辞書は x-strategist.md）
- [ ] 書き出し構文・数字×固有名詞ペアの被りなし
- [ ] 一人称が「僕」／ハッシュタグ・DM誘導・自社名なし

## 6. 絡み候補プール5件（手動投稿用・品質最優先）

以下の3条件を**全部**満たすこと（機械検証必須）:

1. **24時間以内の投稿**: ツイートIDから投稿時刻を必ず検証（過去に127日前・146日前の化石投稿が混入した事故あり）
   ```bash
   python3 -c "print(__import__('datetime').datetime.fromtimestamp(((ID>>22)+1288834974657)/1000))"
   ```
2. **建設業界に直接関連する内容**（過去に「すだちの豆知識」「個人の休日報告」が混入した事故あり。業界外はどれだけバズってても除外）
3. **いいね50以上 or 投稿者フォロワー2,000以上**（小アカへのリプはインプ0〜30の実測で無駄打ち）

**優先順**: ①A tier（@karube_sanei @inatake0 @TKG_CraftBank @Stoneman_ISHIO @shinkojuki @carpentershoyan @monozukuritarou @sekokan_kun）の24h以内投稿 ②業界紙・記者（@kensetsunews @nikkenko 日経クロステック） ③tier外の建設関連バズ（min_faves 100+）

- 同日の他枠（engage_pool_morning / noon / evening）と同じ投稿は選ばない
- draft はデータ補足型（自分しか出せない数字・事実を1個添える）優先。やさしい口調60〜100字、論理飛躍禁止、DM誘導禁止、自社宣伝禁止

**書き込み先**: dashboard.json の `engage_pool_{枠}` と `engage_cards` の**両方**に同じ5件を書く。
- engage_pool の各候補: `{"url","author","snippet","engagement":{"likes":N,"rts":N},"engage_type":"quote"|"reply","draft","reason"}`
- engage_cards のフィールド: `no, action_type, target_account, name, tier, target_post_url, target_snippet, engagement, text`（textにdraft本文。**Slack通知はengage_cardsを読む**ので旧スキーマだと通知が空欄になる）
- engage_cards は上書きしてよい。他枠の engage_pool_* は維持する。`reply_sales` は書かない

## 7. 画像（必須ではない）

本文の数字を表・比較グラフに**可視化できる時だけ** `image_type='gemini'` + `image_prompt`。手書きメモ風・ノート風は廃止。迷ったら画像なし。

## 8. キュー書き込み

```bash
pip install tweepy python-dotenv google-genai Pillow
```
```python
import sys
sys.path.insert(0, 'scripts')
from post_queue import load_queue, add_post
q = load_queue()
q = add_post(q, today, '07:25', '投稿本文', freshness='locked')
# reply_text は渡さない（v3.2で自己リプ全廃）
# データ可視化できる時だけ image_type='gemini', image_prompt='...' を追加
```

枠ごとの時刻と freshness: 朝 `07:25`/`locked`、昼 `12:00`/`updatable`、夕 `20:00`/`updatable`。

## 9. commit & push

```bash
git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"
# CCRのclone時に仕込まれるApp読み取り専用トークンのextraheaderを除去（push 403の主因。2026-07-13修正）
git config --global --unset-all http.https://github.com/.extraheader 2>/dev/null || true
git config --unset-all http.https://github.com/.extraheader 2>/dev/null || true
git add output/post_queue.json output/dashboard.json
git commit -m "post: <日付> <枠> + 絡み候補5"
git -c http.https://github.com/.extraheader= push https://$PAT@github.com/nittaakihiro/x-auto-post.git HEAD:main
```

PATはルーティンのプロンプト内に埋め込む（**リポ内ファイルには絶対に書かない**。public repoはsecret scanningで即失効する。2026-07-11に実際に失効させた事故あり）。
