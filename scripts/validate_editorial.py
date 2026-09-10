"""Validate a v6 draft handoff offline; this does not judge truth or predict reach."""
import json
from pathlib import Path
from urllib.parse import urlparse

SLOTS = {"morning": "07:25", "noon": "12:00", "evening": "20:00", "night": "21:00"}
FIELDS = ("pillar", "format", "scores", "selection_reason", "source_url", "published_at", "checked_at", "availability", "unverified", "hook_alternative")


def validate(dashboard, queue):
    errors = []
    if dashboard.get("version") != 6:
        return ["dashboard.version must be 6"]
    slot = dashboard.get("slot")
    if slot not in SLOTS:
        return ["unknown slot"]
    for key in ("date", "generated_at"):
        if not dashboard.get(key):
            errors.append(f"missing {key}")
    cards = dashboard.get("engage_cards")
    if not isinstance(cards, list) or len(cards) > 2:
        errors.append("engage_cards must contain 0–2 cards")
    post = dashboard.get("original_post")
    matches = [p for p in queue if p.get("date") == dashboard.get("date") and p.get("time") == SLOTS[slot] and p.get("status") in ("draft", "pending")]
    if post is None:
        if not dashboard.get("skip_reason") or cards or matches:
            errors.append("skip needs reason, empty cards, and no active slot draft")
        return errors
    if not isinstance(post, dict):
        return errors + ["original_post must be an object"]
    if len(matches) != 1:
        return errors + ["expected exactly one current queue draft"]
    queued = matches[0]
    if post.get("status") != "draft" or queued.get("status") != "draft":
        errors.append("manual publication requires draft status")
    if post.get("time") != SLOTS[slot] or not post.get("text") or post.get("text") != queued.get("text"):
        errors.append("dashboard text/time must match current slot")
    editorial = post.get("editorial") or {}
    if editorial != queued.get("editorial"):
        errors.append("queue/dashboard editorial mismatch")
    for key in FIELDS:
        if key not in editorial:
            errors.append(f"missing editorial.{key}")
    scores = editorial.get("scores")
    if not isinstance(scores, dict) or len(scores) != 5 or any(type(v) is not int or not 0 <= v <= 2 for v in scores.values()):
        errors.append("scores must have five integer values 0–2")
    source = urlparse(str(editorial.get("source_url", "")))
    if source.scheme not in ("https", "http") or not source.netloc:
        errors.append("source_url must be a web URL")
    for key in ("selection_reason", "checked_at", "hook_alternative", "availability"):
        if not editorial.get(key):
            errors.append(f"empty editorial.{key}")
    if queued.get("type") == "quote_rt" and not queued.get("quote_tweet_id"):
        errors.append("quote requires quote_tweet_id")
    return errors


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    errors = validate(json.loads((root / "output/dashboard.json").read_text()), json.loads((root / "output/post_queue.json").read_text()))
    for error in errors:
        print(error)
    print("editorial validation failed" if errors else "editorial handoff valid (fact check still required)")
    raise SystemExit(bool(errors))
