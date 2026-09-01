# ClaudeCode研修（建設業特化）スライド

株式会社蔵前様向け Claude Code 研修（全6回）のスライド。
第1〜4回のPDFは Google Drive（`Claude Code研修/株式会社蔵前様/`）にある。

## ファイル

| ファイル | 内容 |
| --- | --- |
| `claudecode-kenshu-05.html` | 第5回スライド（24枚・1280×720px） |
| `build_pdf.sh` | HTML → PDF 書き出しスクリプト |

## 第5回の位置づけ

全6回のうち、前半3回＝Claudeのチャットで書類づくり、後半3回＝Claude Code。

- 第4回（自動化①）: 承認ループ／CLAUDE.md／一括処理／メール連携
- **第5回（自動化②）: 手順書を書く → コマンド化して一言で呼ぶ → 直す・絞る・渡す**
- 第6回（最終回）: 業務への定着

第4回の締め「次回は、その手順書をAIに覚えてもらって『一言で動く』形にします」と、
第4回の宿題「毎回同じ手順でやっている業務を1つ書き出す」を受けた構成。

## 章立て

1. CHAPTER 01 毎回の説明を、1回で終わりにする（置き場3つの整理／手順書の型5行／実習①）
2. CHAPTER 02 一言で呼べる形にしてもらう（コマンドとは／実演3ステップ／実習②）
3. CHAPTER 03 毎週の半日が、5分になります（実演／役割別5例／演習③）
4. CHAPTER 04 直す・絞る・渡す（直し方／「常に許可」の線引き／人に渡す／任せてはいけないこと）

## PDFの作り方

```bash
bash docs/training/build_pdf.sh docs/training/claudecode-kenshu-05.html
```

- 出力: `docs/training/claudecode-kenshu-05.pdf`（1280×720px・24ページ）
- 初回実行時に Noto Sans JP を `docs/training/fonts/` へ取得する（リポジトリには含めない）
- Chromium が自動で見つからない場合は `CHROME=/path/to/chrome` を指定する

配布用のファイル名は他の回に合わせて `ClaudeCode研修_建設業特化_第5回.pdf` にリネームする。
