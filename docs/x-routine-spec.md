# ルーティン仕様 v7.2（morning/noon/evening/night）
戦略の正本 docs/x-strategist.md（v7.2・2026-10-05）を必ず全文読む。型・口調・配分は v7.2 が最優先（特に v7.2 の5つ：現場でこう使える／タグは原則なし／英語の引用元には解説／結論は本人のポジションと噛み合わせる／入口は直近のニュース）。dashboard と editorial のスキーマは v6 のまま（version=6・validate_editorial.py も変更なし）。
既存4枠のスケジュール・認証・Slack宛先は保持。Xは手動公開、status='draft'。

1. 最新mainを取得。news_feed、ai_buzz、slack_buzz、直近14日のキュー、最新dashboardを読む。前枠だけでなく実投稿の重複も確認。取得できなければ実投稿未確認と記す。
2. 朝＝一般AIの大ネタ速報（公式のデモ動画など動く素材があるものだけ。無ければ休載）、昼＝海外の建設AIのすげーニュース1本目、夕＝本質投稿（文字だけ・正本の柱3。8点未満なら建設AI/AIの動画付き投稿への引用に切り替え）、夜＝海外の建設AIのすげーニュース2本目（昼と別ネタ。無ければ海外AIの驚くデモ動画。48h以内に動く素材つきの候補ゼロの日は休載）。ニュース枠（朝・昼・夜・土曜）は video_url を付けられないネタを採用しない。解説記事・調査・市場予測は採用しない。国内外を検索し候補5件を比較。競合サービスの紹介は戦略の除外ルールに従い、本文・補足・引用・リプ・RT候補から外す。
3. ニュース枠は戦略の5観点（驚き・絵・鮮度・建設との距離・確かさ）、夕の本質投稿は本質の5観点（主張・仕組み・具体・建設固有・判断）で各0〜2点評価。一次本文を開いて利用条件と日付を確認。採用ネタに編集上の理由を一文でつける。スコアは主観的な編集基準でありバズ予測ではない。
4. 戦略の型（速報型／本質型／引用型）をチャエンの見本どおりに使う。速報型は見出しの1文（タグは本当に大きな発表の時だけ）→本音1〜2行→（英語の引用元なら解説の段落）→数字入りの箇条3〜4つ→「↓詳細」、本文に建設の誰がどの作業でどう使えるかを1〜2行、自己リプに■ 補足と■ 出典。口調はです・ますとタメ口の混在。冒頭を2案作り、驚きが一瞬で伝わる方を採用。
5. 完成文＋出典＋素材URLを作り、セルフレビュー。原文と数字・提供条件の一致、未確認体験の不在（ルーティンは作ってみたを書かない）、重複をチェック。タグは本当に大きな発表の時だけ。英語の引用元に解説があるか、入口が直近48hの出来事か、締めがAIを後回しにする向きになっていないか（新田さんが言って違和感がないか）を確認。
6. post_queue.add_postで今回枠を追加。時刻は07:25/12:00/20:00/21:00。status='draft'必須。引用ならpost_type='quote_rt', quote_tweet_id。画像なしはimage_type='none'。video_urlがあれば画像不要。reply_textは追加説明/出典が必要な時だけ。
7. 追加したentryにeditorial={pillar, format, scores, selection_reason, source_url, published_at, checked_at, availability, unverified, hook_alternative}を追加し、save_queueでキューを保存。既存フィールドは壊さない。
8. dashboardはversion=6, slot（morning/noon/evening/night）を必ず設定し、既存互換のdate/post_date/generated_at/original_post/engage_cardsを維持。過去のnoon_post/evening_post/night_postやrepost_*は持ち越さない。original_postは今回分だけ、time/text/status/article_url/video_url/reply_text/editorialを入れる。推奨引用・リプは0〜2件、既存カード形式を使う。追加のRT候補は任意。
9. 採用なしでも当日の枠のdashboardを生成しoriginal_post=null, engage_cards=[], skip_reason, slot, generated_atを保存する。生成失敗と意図した休載を区別する。
10. python3 scripts/validate_editorial.py を実行。失敗は修正してからcommit。git diffを確認し、output/post_queue.jsonとoutput/dashboard.jsonだけcommit。最新mainへrebaseしてpush。競合や失敗を握りつぶさず報告。認証は既存環境を使用し秘密をリポジトリやログに書かない。

Slackは今回の完成文・推奨引用/リプ先・出典・確認事項を届ける。画像生成は今回の投稿に必要な時だけ。過去枠を再生成/再送しない。
Xへの自動投稿開始、新しい有料API利用は行わない。既存ルーティンの障害は成功したふりをせず、最終生成時刻・失敗工程を明示する。
