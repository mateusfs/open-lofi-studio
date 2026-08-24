from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from youtube_outreach.models import CommentEntry, Limits, VideoCandidate


def load_log(log_path: Path) -> list[CommentEntry]:
    if not log_path.exists():
        return []
    raw = json.loads(log_path.read_text(encoding="utf-8"))
    return [
        CommentEntry(
            video_id=item["videoId"],
            channel_id=item["channelId"],
            comment_id=item["commentId"],
            posted_at=item["postedAt"],
            text=item["text"],
            channel_name=item["channelName"],
            video_title=item["videoTitle"],
        )
        for item in raw.get("entries", [])
    ]


def save_log(log_path: Path, entries: list[CommentEntry]) -> None:
    payload = {
        "entries": [
            {
                "videoId": entry.video_id,
                "channelId": entry.channel_id,
                "commentId": entry.comment_id,
                "postedAt": entry.posted_at,
                "text": entry.text,
                "channelName": entry.channel_name,
                "videoTitle": entry.video_title,
            }
            for entry in entries
        ]
    }
    log_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def append_log_entry(log_path: Path, entry: CommentEntry) -> None:
    entries = load_log(log_path)
    if any(existing.video_id == entry.video_id for existing in entries):
        return
    entries.append(entry)
    save_log(log_path, entries)


def has_commented_on_video(entries: list[CommentEntry], video_id: str) -> bool:
    return any(entry.video_id == video_id for entry in entries)


def count_comments_since(entries: list[CommentEntry], since: datetime) -> int:
    count = 0
    for entry in entries:
        posted = datetime.fromisoformat(entry.posted_at.replace("Z", "+00:00"))
        if posted >= since:
            count += 1
    return count


def last_comment_on_channel(
    entries: list[CommentEntry], channel_id: str
) -> datetime | None:
    matching = [
        datetime.fromisoformat(entry.posted_at.replace("Z", "+00:00"))
        for entry in entries
        if entry.channel_id == channel_id
    ]
    if not matching:
        return None
    return max(matching)
