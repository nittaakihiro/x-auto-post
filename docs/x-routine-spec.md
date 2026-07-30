# ルーティン共通仕様 v4（x-post-morning / noon / evening）

戦略・文体・NG表現の正本は `docs/x-strategist.md`（v4）。この文書は**3ルーティン共通の手順仕様**だけを持つ。矛盾したら x-strategist.md が勝つ。

2026-07-30 v4改訂: 休載ルール新設 / ゲート5の型化防止 / 絡みカード5件→各枠1枚の完成文形式 / 夜枠は引用RT型 / 土曜朝はフラッグシップ。

---

## 0. 休載ルール（v4新設・薄いネタで枠を埋めない）

- ゲート（§1）を**3回試行して通らなければ、その枠は休載**する。`add_post` を呼ばず、絡みカード（§6）だけ書いてcommitする。commitメッセージに `skip: <枠> <理由>` を書く
- ただし過去7日の投稿数（post_queueのoriginal + フラッグシップ）が**5本を下回りそうな場合だけ**、基準内の最良案で埋める
- 夜枠（C型）はデフォルト厳しめでよい: 鋭い構造暴露がない日は休載し、引用RTカードだけ出す

## 1. 投稿の必須要素ゲート（1つでも欠けたら没にして別ネタ・最大3回試行）

1. **実名1つ以上**（企業名 / 制度名 / 省庁名 / 統計名。出典が言える実データ）
2. **数字2つ以上**（%・円・件数・人数・日付）
3. **新情報1つ以上**（読者がブックマークか引用したくなる）
4. **現場への含意1行**（格言・標語ではなく具体で）
5. **一人称の一次観点を1文以上**

### ゲート5の書き方（v4: 型化防止を追加）

- ○ 「僕は〜と思ってる」「〜が気になった」等、新田本人の判断・解釈・違和感を地の文で書く
- **「僕は見てる」「僕は思う」は同一投稿内で合計1回まで**（7/28〜30の9本が全部この同型2連で締めており、型化するとニュースbotの新しい皮になるだけ）
- 表現をローテ: 驚いた / 引っかかった / 違和感がある / 正直〜だと読んでる / うちなら〜する / 現場で聞く話と重なる。**直近5投稿と同じ一人称表現は使わない**（post_queueで確認）
- **週2本は一人称の判断を1〜2行目に置く**（過去7日のpost_queueで冒頭型がゼロなら今回は冒頭に置く）
- ✕ 創作した商談・訪問・会話（実際に起きたことだけ） / ✕ 伝聞ヘッジ / ✕ コンサル一般論への着地
- エピソードバンクは本文使用禁止。ネタが無ければ事実＋自分の解釈でゲート5を満たす

## 2. 自己リプは作らない（維持）

`add_post` に `reply_text` を**渡さない**。ソースURLリプ廃止。出典は本文内に「機関名＋発表日」で書く。URLは本文にもリプにも載せない（`source_url` はdashboard.jsonに残すだけ）。

## 3. マンネリチェック（維持）

過去14日の post_queue.json のオリジナル投稿を読んで、(1)同一の具体的数字×固有名詞ペアの再利用禁止（ジャンル自体は新事実が出れば毎週OK） (2)直近5投稿と同じ書き出し構文禁止 (3)直近5投稿と同じ一人称表現禁止（v4追加）を守る。

```bash
python3 -c "
import json
from datetime import datetime,timezone,timedelta
JST=timezone(timedelta(hours=9)); cutoff=(datetime.now(JST)-timedelta(days=14)).strftime('%Y-%m-%d')
posts=[p for p in json.load(open('output/post_queue.json')) if p.get('date','')>=cutoff and p.get('type')=='original']
print(chr(10).join(p.get('date','')+' '+p.get('text','') for p in posts[-25:]))"
```

## 4. ネタ収集（維持）

WebSearchで収集。鉄板ジャンル: 資材供給・値上げ / ゼネコン・住設の決算と再編 / 制度改正＋施行日・締切 / 労務単価・賃金・人手 / 倒産・資金繰りの構造 / 建設テック動向。

ニュースは72h以内優先、統計は発表6ヶ月以内のみ。**ファクトチェック必須**: 企業名・数字・制度名・日付はWebSearchで裏取りし、裏取り不能な要素は削るか没にする。

## 5. 土曜朝はフラッグシップ（v4新設・x-post-morningのみ）

土曜の朝枠は通常のA型ではなく**「今週の建設業、数字で3つ」**を書く:

- その週（月〜金）の統計・決算・制度ニュースから3つ選ぶ（各ネタは72h制限の例外。その週のものならOK）
- 構成: 導入1行 → 数字ごとに「1行事実+1行僕の解釈」×3 → 総括の一人称1行。300字級フル尺
- 型（見出し行・番号の振り方）は毎週同じにする。看板として認知させる
- 各数字は本文中で「機関名＋発表日」を添える。ゲート・文体・マンネリチェックは通常通り
- 数字が3つ以上並ぶので表画像（`image_type='gemini'`）を付けてよい（迷ったら無し）

## 6. 絡みカード: 各枠1枚だけ・完成文形式（v4で5件プール廃止）

**このカードの目的は新田さんがコピペ10秒で投稿を完了すること。** 候補を並べる資料ではない。

- **各ルーティンは最良の1枚だけ**を書く。朝・昼=**リプ型**、夜=**引用RT型**（相手の投稿に自分しか出せない数字・事実を1個足す。「同意です」だけの引用は没）
- 3条件AND（機械検証必須）:
  1. **24時間以内の投稿**（snowflakeで検証・**6時間以内を優先**）
     ```bash
     python3 -c "print(__import__('datetime').datetime.fromtimestamp(((ID>>22)+1288834974657)/1000))"
     ```
  2. **建設業界に直接関連する内容**（業界外はどれだけバズってても除外）
  3. **いいね50以上 or 投稿者フォロワー2,000以上**
- 優先順: ①A tier（@karube_sanei @inatake0 @TKG_CraftBank @Stoneman_ISHIO @shinkojuki @carpentershoyan @monozukuritarou @sekokan_kun）の6h以内投稿 ②業界紙・記者（@kensetsunews @nikkenko 日経クロステック） ③tier外の建設関連バズ（min_faves 100+）
- 同日の他枠のカードと同じ投稿・同じ相手は選ばない（dashboard.jsonの他枠カードを確認）
- **draftは完成文**: そのまま投稿できる形で書く。やさしい口調60〜100字、データ補足型（自分しか出せない数字・事実を1個）優先、論理飛躍禁止、DM誘導禁止、自社宣伝禁止
- 条件を満たす候補が本当に無い枠は絡みカード無しでよい（無理に埋めない）

**書き込み先**: dashboard.json の `engage_cards` に**その枠の1枚だけ**（上書きOK）。`engage_pool_{枠}` にも同じ1枚を書く（互換用）。`reply_sales` は書かない。
- engage_cards のフィールド: `no, action_type("reply"|"quote"), target_account, name, tier, target_post_url, target_snippet, engagement, text`（**textは完成文**。Slack通知はengage_cardsを読む）

## 7. セルフチェック（生成後に必ず実行）

- [ ] ゲート5項目すべて（休載判断を含む: 3回落ちたら休載）
- [ ] **「僕は見てる/思う」が合計1回以下・直近5投稿と一人称表現が被っていない**
- [ ] 100〜300字（朝枠・土曜フラッグシップは250〜300 / 夕枠C型は90字台可）
- [ ] 空行ゼロ・文ごと改行済み（本文3行以上）
- [ ] URLが本文に入っていない / reply_text を渡していない
- [ ] AI臭ワード2未満（辞書は x-strategist.md）
- [ ] 書き出し構文・数字×固有名詞ペアの被りなし
- [ ] 一人称が「僕」／ハッシュタグ・DM誘導・自社名なし
- [ ] 絡みカードのtextが完成文になっている（編集しないと投稿できない下書きはNG）

## 8. 画像（維持・必須ではない）

本文の数字を表・比較グラフに**可視化できる時だけ** `image_type='gemini'` + `image_prompt`。手書きメモ風・ノート風は廃止。迷ったら画像なし。

## 9. キュー書き込み（維持）

```bash
pip install tweepy python-dotenv google-genai Pillow
```
```python
import sys
sys.path.insert(0, 'scripts')
from post_queue import load_queue, add_post
q = load_queue()
q = add_post(q, today, '07:25', '投稿本文', freshness='locked')
# reply_text は渡さない（自己リプ全廃）
# データ可視化できる時だけ image_type='gemini', image_prompt='...' を追加
```

枠ごとの時刻と freshness: 朝 `07:25`/`locked`、昼 `12:00`/`updatable`、夕 `20:00`/`updatable`。

## 10. commit & push（維持）

```bash
git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"
# CCRのclone時に仕込まれるApp読み取り専用トークンのextraheaderを除去（push 403の主因。2026-07-13修正）
git config --global --unset-all http.https://github.com/.extraheader 2>/dev/null || true
git config --unset-all http.https://github.com/.extraheader 2>/dev/null || true
git add output/post_queue.json output/dashboard.json
git commit -m "post: <日付> <枠>（休載時は skip: <枠> <理由>）"
git -c http.https://github.com/.extraheader= push https://$PAT@github.com/nittaakihiro/x-auto-post.git HEAD:main
```

PATはルーティンのプロンプト内に埋め込む（**リポ内ファイルには絶対に書かない**。public repoはsecret scanningで即失効する。2026-07-11に実際に失効させた事故あり）。
