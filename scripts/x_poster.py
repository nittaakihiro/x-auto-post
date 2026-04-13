#!/usr/bin/env python3
"""
X (Twitter) API 投稿モジュール
tweepy v2 を使って投稿・リプライ・引用RTを行う。

使い方:
  from x_poster import XPoster
  poster = XPoster()  # .envから自動読み込み

  # 通常投稿
  tweet_id = poster.post("投稿テキスト")

  # リプライ（自分の投稿に返信）
  poster.reply(tweet_id, "リプライテキスト")

  # 引用RT
  poster.quote("引用コメント", quote_tweet_id="1234567890")

  # スレッド投稿
  ids = poster.thread(["1つ目", "2つ目", "3つ目"])
"""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

# 全HTTP呼び出しのデフォルトタイムアウト（昨日の17時間SSL readハング再発防止）
socket.setdefaulttimeout(60)

import tweepy
from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
    from PIL import Image
    from io import BytesIO
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# .env読み込み（scripts/の親ディレクトリ = プロジェクトルート）
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")


class XPoster:
    """X API v2 投稿クライアント"""

    def __init__(self):
        self.api_key = os.environ["X_API_KEY"]
        self.api_secret = os.environ["X_API_SECRET"]
        self.access_token = os.environ["X_ACCESS_TOKEN"]
        self.access_secret = os.environ["X_ACCESS_TOKEN_SECRET"]

        self.client = tweepy.Client(
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_secret,
        )
        # v1.1 API（画像アップロード用）
        auth = tweepy.OAuth1UserHandler(
            self.api_key, self.api_secret,
            self.access_token, self.access_secret,
        )
        self.api_v1 = tweepy.API(auth)
        self._user_id = None

    @property
    def user_id(self):
        """認証ユーザーのIDを取得（初回のみAPI呼び出し）"""
        if self._user_id is None:
            me = self.client.get_me()
            self._user_id = me.data.id
        return self._user_id

    def upload_media(self, image_path: str) -> str:
        """画像をアップロードしてmedia_idを返す。"""
        media = self.api_v1.media_upload(filename=image_path)
        print(f"[MEDIA] アップロード成功: {media.media_id}")
        return str(media.media_id)

    def post(self, text: str, media_ids: list[str] = None) -> str:
        """通常投稿。画像付き可。投稿IDを返す。"""
        kwargs = {"text": text}
        if media_ids:
            kwargs["media_ids"] = media_ids
        resp = self.client.create_tweet(**kwargs)
        tweet_id = resp.data["id"]
        img_note = f" (画像{len(media_ids)}枚)" if media_ids else ""
        print(f"[POST] 投稿成功: {tweet_id}{img_note}")
        return tweet_id

    def reply(self, in_reply_to_id: str, text: str) -> str:
        """リプライ投稿。投稿IDを返す。"""
        resp = self.client.create_tweet(
            text=text,
            in_reply_to_tweet_id=in_reply_to_id,
        )
        tweet_id = resp.data["id"]
        print(f"[REPLY] リプライ成功: {tweet_id} → {in_reply_to_id}")
        return tweet_id

    def quote(self, text: str, quote_tweet_id: str) -> str:
        """引用RT。投稿IDを返す。"""
        resp = self.client.create_tweet(
            text=text,
            quote_tweet_id=quote_tweet_id,
        )
        tweet_id = resp.data["id"]
        print(f"[QUOTE] 引用RT成功: {tweet_id} → {quote_tweet_id}")
        return tweet_id

    def thread(self, texts: list[str], media_ids: list[str] = None) -> list[str]:
        """スレッド投稿。各投稿IDのリストを返す。media_idsは1つ目の投稿に添付。"""
        if not texts:
            return []
        ids = []
        # 1つ目は通常投稿（画像付き可）
        first_id = self.post(texts[0], media_ids=media_ids)
        ids.append(first_id)
        # 2つ目以降はリプライチェーン
        prev_id = first_id
        for t in texts[1:]:
            reply_id = self.reply(prev_id, t)
            ids.append(reply_id)
            prev_id = reply_id
        print(f"[THREAD] スレッド投稿完了: {len(ids)}件")
        return ids

    def get_my_tweets(self, count: int = 20) -> list[dict]:
        """自分の直近投稿を取得。[{"id", "text", "created_at"}]のリストを返す。"""
        resp = self.client.get_users_tweets(
            id=self.user_id,
            max_results=min(count, 100),
            tweet_fields=["created_at", "public_metrics"],
            exclude=["replies", "retweets"],
            user_auth=True,
        )
        if not resp.data:
            return []
        tweets = []
        for t in resp.data:
            tweets.append({
                "id": t.id,
                "text": t.text,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "metrics": t.public_metrics,
            })
        print(f"[TIMELINE] 直近{len(tweets)}件取得")
        return tweets

    def generate_image(self, prompt: str, save_path: str) -> str | None:
        """Gemini APIで画像を生成してローカルに保存。パスを返す。"""
        if not HAS_GEMINI:
            print("[WARN] google-genai/Pillow未インストール。画像生成スキップ。")
            return None

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("[WARN] GEMINI_API_KEY未設定。画像生成スキップ。")
            return None

        client = genai.Client(api_key=api_key)
        config = types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"])

        import time
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model="gemini-3.1-flash-image-preview",
                    contents=prompt,
                    config=config,
                )
                for part in response.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                        img = Image.open(BytesIO(part.inline_data.data))
                        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                        img.save(save_path, format="PNG")
                        print(f"[GEMINI] 画像生成成功: {save_path} ({img.size[0]}x{img.size[1]})")
                        return save_path
                print(f"[GEMINI] 画像なし。リトライ {attempt + 2}/3...")
                time.sleep(3)
            except Exception as e:
                print(f"[GEMINI] エラー: {e}")
                if attempt < 2:
                    time.sleep(5 * (attempt + 1))
        return None

    def verify(self) -> dict:
        """認証テスト。ユーザー情報を返す。"""
        me = self.client.get_me()
        info = {
            "id": me.data.id,
            "name": me.data.name,
            "username": me.data.username,
        }
        print(f"[AUTH] 認証成功: @{info['username']} ({info['name']})")
        return info


if __name__ == "__main__":
    poster = XPoster()
    poster.verify()
