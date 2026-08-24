from __future__ import annotations

import json
from pathlib import Path

from youtube_outreach.models import (
    CommentRules,
    Discovery,
    Limits,
    OurChannel,
    OutreachConfig,
    TargetChannel,
)


def load_outreach_config(config_path: Path) -> OutreachConfig:
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    our = raw["ourChannel"]
    limits_raw = raw["limits"]
    discovery_raw = raw.get("discovery", {})
    rules_raw = raw["commentRules"]
    channels = [
        TargetChannel(
            handle=item["handle"],
            name=item["name"],
            channel_id=item.get("channelId"),
            priority=item["priority"],
            comment_angle=item["commentAngle"],
        )
        for item in raw["targetChannels"]
    ]
    channels.sort(key=lambda channel: channel.priority)
    return OutreachConfig(
        our_channel=OurChannel(
            name=our["name"],
            handle=our["handle"],
            url=our["url"],
        ),
        limits=Limits(
            max_candidates_per_run=limits_raw.get("maxCandidatesPerRun", 15),
            max_comments_per_run=limits_raw["maxCommentsPerRun"],
            max_comments_per_day=limits_raw.get(
                "maxCommentsPerDay",
                limits_raw["maxCommentsPerRun"],
            ),
            max_comments_per_week=limits_raw["maxCommentsPerWeek"],
            min_days_between_same_channel=limits_raw["minDaysBetweenSameChannel"],
            max_video_age_days=limits_raw["maxVideoAgeDays"],
        ),
        discovery=Discovery(
            enabled=discovery_raw.get("enabled", False),
            max_results_per_query=discovery_raw.get("maxResultsPerQuery", 10),
            queries=tuple(discovery_raw.get("queries", [])),
            excluded_title_terms=tuple(
                discovery_raw.get("excludedTitleTerms", [])
            ),
        ),
        comment_rules=CommentRules(
            language=rules_raw["language"],
            min_length=rules_raw["minLength"],
            max_length=rules_raw["maxLength"],
            max_emojis=rules_raw["maxEmojis"],
            max_links=rules_raw["maxLinks"],
            forbidden_phrases=tuple(rules_raw["forbiddenPhrases"]),
        ),
        soft_mention_templates=tuple(raw["softMentionTemplates"]),
        target_channels=channels,
        config_path=str(config_path),
    )


def save_channel_ids(config_path: Path, channels: list[TargetChannel]) -> None:
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    by_handle = {channel.handle: channel.channel_id for channel in channels}
    for item in raw["targetChannels"]:
        item["channelId"] = by_handle.get(item["handle"])
    config_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
