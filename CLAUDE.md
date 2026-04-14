# X Auto Post System

## 概要
このリポジトリはX（Twitter）の自動投稿システム。
- `scripts/auto_post.py` — キューから自動投稿（GitHub Actionsで実行）
- `scripts/post_queue.py` — キュー管理モジュール
- `scripts/x_poster.py` — X API投稿クライアント
- `output/post_queue.json` — 投稿キュー（これに書き込めば自動投稿される）

## リモートエージェント（投稿生成）の手順

毎朝7:00 JSTにリモートエージェントが起動し、以下を実行する:

### 1. マンネリチェック
- `scripts/` ディレクトリで以下を実行して直近投稿を取得:
  ```bash
  cd scripts && python3 -c "from x_poster import XPoster; import json; print(json.dumps(XPoster().get_my_tweets(20), ensure_ascii=False, indent=2))"
  ```
- 直近20件のテーマ・フレーズを分析し、被りを特定 → 今日は使わない

### 2. Slack #x-influencer-watch から絡み先取得
- **Slack MCPは使わない。代わりにfetch_slack.pyを実行:**
  ```bash
  cd scripts && SLACK_BOT_TOKEN="$SLACK_BOT_TOKEN" python3 fetch_slack.py
  ```
- 環境変数 `SLACK_BOT_TOKEN` はトリガープロンプトの冒頭で `export` する
- x.comのURLが含まれる投稿をピックアップし、絡みカードのネタにする

### 3. リサーチ
- WebSearchで建設業の最新ニュース・トレンドを調査
- 検索クエリ例:
  - `建設業 AI 最新ニュース`
  - `建設DX 2026`
  - `建設業 site:x.com min_faves:100`
  - `国交省 建設業 プレスリリース`

### 4. オリジナル投稿3本を生成
- `docs/x-strategist.md` のルールに従う
- 投稿時刻: 7:30 / 12:00 / 20:00
- 各投稿にリプライ文も用意

### 5. post_queue.json に書き込み
- `scripts/post_queue.py` の `add_post()` を使うか、直接JSONを編集
- 既存のキューエントリは上書きしない（appendのみ）

### 6. commit & push
- 変更をcommit+pushしてGitHub Actionsに投稿を引き渡す

## 注意事項
- 引用RT・リプライはキューに入れない（API制限で失敗するため）
- オリジナル投稿のみキューに登録する
- 自社サービス名（ツクノビ、BPO等）は本文に入れない → リプで分離
