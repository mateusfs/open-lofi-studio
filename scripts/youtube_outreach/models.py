from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OurChannel:
    name: str
    handle: str
    url: str


@dataclass(frozen=True)
class Limits:
    max_candidates_per_run: int
    max_comments_per_run: int
    max_comments_per_day: int
    max_comments_per_week: int
    min_days_between_same_channel: int
    max_video_age_days: int


@dataclass(frozen=True)
class Discovery:
    enabled: bool
    max_results_per_query: int
    queries: tuple[str, ...]
    excluded_title_terms: tuple[str, ...]


@dataclass(frozen=True)
class CommentRules:
    language: str
    min_length: int
    max_length: int
    max_emojis: int
    max_links: int
    forbidden_phrases: tuple[str, ...]


@dataclass
class TargetChannel:
    handle: str
    name: str
    channel_id: str | None
    priority: int
    comment_angle: str


@dataclass(frozen=True)
class VideoCandidate:
    video_id: str
    title: str
    channel_id: str
    channel_name: str
    published_at: datetime
    url: str


@dataclass(frozen=True)
class CommentEntry:
    video_id: str
    channel_id: str
    comment_id: str
    posted_at: str
    text: str
    channel_name: str
    video_title: str


@dataclass(frozen=True)
class OutreachConfig:
    our_channel: OurChannel
    limits: Limits
    discovery: Discovery
    comment_rules: CommentRules
    soft_mention_templates: tuple[str, ...]
    target_channels: list[TargetChannel]
    config_path: str
