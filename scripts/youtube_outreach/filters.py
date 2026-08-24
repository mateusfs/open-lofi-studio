from __future__ import annotations

from datetime import UTC, datetime, timedelta

from youtube_outreach.log_store import count_comments_since, has_commented_on_video, last_comment_on_channel
from youtube_outreach.models import CommentEntry, Limits, VideoCandidate


def is_video_too_old(published_at: datetime, max_age_days: int, now: datetime | None = None) -> bool:
    reference = now or datetime.now(UTC)
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    cutoff = reference - timedelta(days=max_age_days)
    return published_at < cutoff


def is_channel_on_cooldown(
    entries: list[CommentEntry],
    channel_id: str,
    min_days: int,
    now: datetime | None = None,
) -> bool:
    last = last_comment_on_channel(entries, channel_id)
    if last is None:
        return False
    reference = now or datetime.now(UTC)
    return last > reference - timedelta(days=min_days)


def weekly_limit_reached(
    entries: list[CommentEntry],
    max_per_week: int,
    now: datetime | None = None,
) -> bool:
    reference = now or datetime.now(UTC)
    since = reference - timedelta(days=7)
    return count_comments_since(entries, since) >= max_per_week


def filter_candidates(
    candidates: list[VideoCandidate],
    entries: list[CommentEntry],
    limits: Limits,
    now: datetime | None = None,
) -> list[VideoCandidate]:
    reference = now or datetime.now(UTC)
    if weekly_limit_reached(entries, limits.max_comments_per_week, reference):
        return []

    filtered: list[VideoCandidate] = []
    seen_channels: set[str] = set()

    for candidate in candidates:
        if has_commented_on_video(entries, candidate.video_id):
            continue
        if is_video_too_old(candidate.published_at, limits.max_video_age_days, reference):
            continue
        if is_channel_on_cooldown(
            entries,
            candidate.channel_id,
            limits.min_days_between_same_channel,
            reference,
        ):
            continue
        if candidate.channel_id in seen_channels:
            continue
        filtered.append(candidate)
        seen_channels.add(candidate.channel_id)

    return filtered
