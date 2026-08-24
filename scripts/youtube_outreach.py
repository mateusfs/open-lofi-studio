#!/usr/bin/env python3
"""Outreach híbrido: descobre vídeos, gera comentários e publica após aprovação."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

from load_env import ensure_env_file, load_env
from youtube_outreach.comment_generator import generate_comment
from youtube_outreach.config import load_outreach_config, save_channel_ids
from youtube_outreach.filters import filter_candidates
from youtube_outreach.log_store import append_log_entry, count_comments_since, load_log
from youtube_outreach.models import CommentEntry, TargetChannel, VideoCandidate
from youtube_outreach.youtube_client import (
    YouTubeClient,
    build_client_secrets_file,
    resolve_all_channel_ids,
    run_oauth_flow,
)

ensure_env_file()
load_env()

CONFIG_PATH = ROOT / "assets/youtube-outreach-config.json"
LOG_PATH = ROOT / "assets/youtube-outreach-log.json"
DEFAULT_TOKEN_PATH = ROOT / ".credentials/youtube-oauth.json"
DEFAULT_SECRETS_PATH = ROOT / ".credentials/youtube-client-secrets.json"


class OpenAITextGenerator:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def generate(self, prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You write calm, specific YouTube comments for a developer "
                        "focus ambience channel. Output only the comment."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI returned empty comment")
        return content


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YouTube outreach comments for Ambience Session")
    parser.add_argument("--dry-run", action="store_true", help="Preview candidates without posting")
    parser.add_argument("--auth", action="store_true", help="Run OAuth flow and save token")
    parser.add_argument("--no-llm", action="store_true", help="Use template fallback instead of OpenAI")
    parser.add_argument("--max", type=int, default=None, help="Max comments this run")
    parser.add_argument(
        "--candidates",
        type=int,
        default=None,
        help="Max candidate videos to review this run",
    )
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="Outreach config path")
    parser.add_argument("--log", type=Path, default=LOG_PATH, help="Outreach log path")
    parser.add_argument(
        "--token-path",
        type=Path,
        default=Path(os.environ.get("YOUTUBE_OAUTH_TOKEN_PATH", str(DEFAULT_TOKEN_PATH))),
        help="OAuth token file",
    )
    return parser.parse_args()


def token_path_from_env(args: argparse.Namespace) -> Path:
    env_path = os.environ.get("YOUTUBE_OAUTH_TOKEN_PATH")
    if env_path:
        return Path(env_path)
    return args.token_path


def secrets_path_from_env() -> Path:
    return DEFAULT_SECRETS_PATH


def ensure_client_secrets() -> Path:
    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
    secrets_path = secrets_path_from_env()
    if client_id and client_secret:
        return build_client_secrets_file(client_id, client_secret, secrets_path)
    if secrets_path.exists():
        return secrets_path
    raise RuntimeError(
        "Missing YouTube OAuth credentials. Set YOUTUBE_CLIENT_ID and "
        "YOUTUBE_CLIENT_SECRET in .env or place client secrets at "
        f"{secrets_path}"
    )


def collect_candidates(
    client: YouTubeClient,
    channels: list[TargetChannel],
    discovery_queries: tuple[str, ...] = (),
    discovery_results_per_query: int = 10,
    excluded_title_terms: tuple[str, ...] = (),
    max_video_age_days: int = 14,
    per_channel: int = 3,
) -> list[VideoCandidate]:
    candidates: list[VideoCandidate] = []
    for channel in channels:
        try:
            videos = client.fetch_recent_videos(channel, max_results=per_channel)
            candidates.extend(videos)
        except Exception as error:
            print(f"Skip {channel.name}: {error}", file=sys.stderr)
    published_after = datetime.now(UTC) - timedelta(days=max_video_age_days)
    for query in discovery_queries:
        try:
            candidates.extend(
                client.search_recent_videos(
                    query,
                    published_after=published_after,
                    max_results=discovery_results_per_query,
                )
            )
        except Exception as error:
            print(f"Skip discovery query '{query}': {error}", file=sys.stderr)

    unique_candidates = {}
    for candidate in candidates:
        lowered_title = candidate.title.lower()
        if any(term.lower() in lowered_title for term in excluded_title_terms):
            continue
        unique_candidates[candidate.video_id] = candidate
    return sorted(
        unique_candidates.values(),
        key=lambda item: item.published_at,
        reverse=True,
    )


def find_channel_angle(channels: list[TargetChannel], channel_id: str) -> str:
    for channel in channels:
        if channel.channel_id == channel_id:
            return channel.comment_angle
    return "focus and ambience for deep work"


def prompt_approval(index: int, total: int, candidate: VideoCandidate, comment: str) -> str:
    print()
    print(f"[{index}/{total}] {candidate.channel_name} — \"{candidate.title}\"")
    print(f"URL: {candidate.url}")
    print()
    print("Comment:")
    print(comment)
    print()
    while True:
        choice = input("Post? [y/N/s=skip/q=quit]: ").strip().lower()
        if choice in {"", "n", "no"}:
            return "skip"
        if choice in {"y", "yes"}:
            return "post"
        if choice in {"s", "skip"}:
            return "skip"
        if choice in {"q", "quit"}:
            return "quit"
        print("Invalid choice. Use y, n, s, or q.")


def run_auth(token_path: Path) -> None:
    secrets_path = ensure_client_secrets()
    run_oauth_flow(token_path, secrets_path)
    print(f"OAuth token saved to {token_path}")


def build_text_generator(use_llm: bool) -> OpenAITextGenerator | None:
    if not use_llm:
        return None
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("OPENAI_API_KEY missing, using template fallback.", file=sys.stderr)
        return None
    return OpenAITextGenerator(api_key=api_key)


def main() -> int:
    args = parse_args()
    token_path = token_path_from_env(args)

    if args.auth:
        run_auth(token_path)
        return 0

    config = load_outreach_config(args.config)
    log_entries = load_log(args.log)
    requested_comments = args.max or config.limits.max_comments_per_run
    comments_last_day = count_comments_since(
        log_entries,
        datetime.now(UTC) - timedelta(days=1),
    )
    comments_this_week = count_comments_since(
        log_entries,
        datetime.now(UTC) - timedelta(days=7),
    )
    daily_capacity = max(
        config.limits.max_comments_per_day - comments_last_day,
        0,
    )
    weekly_capacity = max(
        config.limits.max_comments_per_week - comments_this_week,
        0,
    )
    max_comments = min(requested_comments, daily_capacity, weekly_capacity)
    max_candidates = args.candidates or config.limits.max_candidates_per_run

    secrets_path = ensure_client_secrets()
    client = YouTubeClient.from_credentials(token_path, secrets_path)

    resolved_channels = resolve_all_channel_ids(client, config.target_channels)
    if any(channel.channel_id != original.channel_id for channel, original in zip(resolved_channels, config.target_channels)):
        save_channel_ids(args.config, resolved_channels)
        print(f"Cached channel IDs in {args.config}")

    discovery_queries = config.discovery.queries if config.discovery.enabled else ()
    candidates = collect_candidates(
        client,
        resolved_channels,
        discovery_queries=discovery_queries,
        discovery_results_per_query=config.discovery.max_results_per_query,
        excluded_title_terms=config.discovery.excluded_title_terms,
        max_video_age_days=config.limits.max_video_age_days,
    )
    eligible = filter_candidates(candidates, log_entries, config.limits)
    session_targets = eligible[:max_candidates]

    if not session_targets:
        print("No eligible videos found for outreach this run.")
        return 0
    if not args.dry_run and max_comments == 0:
        print("Daily or weekly publishing limit reached. No comments posted.")
        return 0

    generator = build_text_generator(use_llm=not args.no_llm)
    posted = 0

    for index, candidate in enumerate(session_targets, start=1):
        if not args.dry_run and posted >= max_comments:
            print(f"\nDaily publishing limit reached ({max_comments}).")
            break
        angle = find_channel_angle(resolved_channels, candidate.channel_id)
        comment = generate_comment(candidate, angle, config, generator=generator)

        if args.dry_run:
            print()
            print(f"[{index}/{len(session_targets)}] {candidate.channel_name} — \"{candidate.title}\"")
            print(f"URL: {candidate.url}")
            print()
            print("Comment:")
            print(comment)
            continue

        choice = prompt_approval(index, len(session_targets), candidate, comment)
        if choice == "quit":
            break
        if choice == "skip":
            continue

        comment_id = client.post_comment(candidate.video_id, comment)
        entry = CommentEntry(
            video_id=candidate.video_id,
            channel_id=candidate.channel_id,
            comment_id=comment_id,
            posted_at=datetime.now(UTC).isoformat(),
            text=comment,
            channel_name=candidate.channel_name,
            video_title=candidate.title,
        )
        append_log_entry(args.log, entry)
        posted += 1
        print(f"Posted comment {comment_id}")

    if args.dry_run:
        print(f"\nDry run complete. {len(session_targets)} candidate(s) shown.")
    else:
        print(f"\nSession complete. Posted {posted} comment(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
