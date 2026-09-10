# ルーティン仕様 v6（morning/noon/evening/night）
戦略の正本 docs/x-strategist.md を必ず読む。旧プロンプトの固定型・画像必須・数字ノルマよりv6を優先。
既存4枠のスケジュール・認証・Slack宛先は保持。Xは手動公開、status='draft'。

1. 最新mainを取得。news_feed、ai_buzz、slack_buzz、直近14日のキュー、最新dashboardを読む。前枠だけでなく実投稿の重複も確認。取得できなければ実投稿未確認と記す。
2. 朝＝一般AI、昼＝建設AI/実演、夕＝AI/建設の引用、夜＝強い海外続報がある時だけ追加。国内外を検索し候補5件を比較。競合サービスの紹介は戦略の除外ルールに従い、本文・補足・引用・リプ・RT候補から外す。
3. 戦略の5観点各0〜2点で評価。一次本文を開いて利用条件と日付を確認。採用ネタに編集上の理由を一文でつける。スコアは主観的な編集基準でありバズ予測ではない。
4. 速報・実演・比較・海外事例・引用から形式を選ぶ。冒頭を2案作り、具体性が高く誇張のない方を採用。段落数、感想、箇条書き、建設への接続を機械的に強制しない。
5. 完成文＋出典＋素材URLを作り、セルフレビュー。原文と数字・提供条件の一致、未確認体験の不在、重複、同じ型の連続をチェック。速報タグは鮮度がある時だけ。
6. post_queue.add_postで今回枠を追加。時刻は07:25/12:00/20:00/21:00。status='draft'必須。引用ならpost_type='quote_rt', quote_tweet_id。画像なしはimage_type='none'。video_urlがあれば画像不要。reply_textは追加説明/出典が必要な時だけ。
7. 追加したentryにeditorial={pillar, format, scores, selection_reason, source_url, published_at, checked_at, availability, unverified, hook_alternative}を追加し、save_queueでキューを保存。既存フィールドは壊さない。
8. dashboardはversion=6, slot（morning/noon/evening/night）を必ず設定し、既存互換のdate/post_date/generated_at/original_post/engage_cardsを維持。過去のnoon_post/evening_post/night_postやrepost_*は持ち越さない。original_postは今回分だけ、time/text/status/article_url/video_url/reply_text/editorialを入れる。推奨引用・リプは0〜2件、既存カード形式を使う。追加のRT候補は任意。
9. 採用なしでも当日の枠のdashboardを生成しoriginal_post=null, engage_cards=[], skip_reason, slot, generated_atを保存する。生成失敗と意図した休載を区別する。
10. python3 scripts/validate_editorial.py を実行。失敗は修正してからcommit。git diffを確認し、output/post_queue.jsonとoutput/dashboard.jsonだけcommit。最新mainへrebaseしてpush。競合や失敗を握りつぶさず報告。認証は既存環境を使用し秘密をリポジトリやログに書かない。

Slackは今回の完成文・推奨引用/リプ先・出典・確認事項を届ける。画像生成は今回の投稿に必要な時だけ。過去枠を再生成/再送しない。
Xへの自動投稿開始、新しい有料API利用は行わない。既存ルーティンの障害は成功したふりをせず、最終生成時刻・失敗工程を明示する。
