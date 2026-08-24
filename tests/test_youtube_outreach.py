from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from youtube_outreach.comment_generator import (
    build_fallback_comment,
    generate_comment,
    infer_mood,
    validate_comment,
)
from youtube_outreach.config import load_outreach_config, save_channel_ids
from youtube_outreach.filters import (
    filter_candidates,
    is_channel_on_cooldown,
    is_video_too_old,
    weekly_limit_reached,
)
from youtube_outreach.log_store import (
    append_log_entry,
    count_comments_since,
    has_commented_on_video,
    load_log,
    save_log,
)
from youtube_outreach.models import (
    CommentEntry,
    CommentRules,
    Discovery,
    Limits,
    OurChannel,
    OutreachConfig,
    TargetChannel,
    VideoCandidate,
)
from youtube_outreach.youtube_client import (
    YouTubeClient,
    build_client_secrets_file,
    load_credentials,
    resolve_all_channel_ids,
    save_credentials,
)


def sample_config() -> OutreachConfig:
    return OutreachConfig(
        our_channel=OurChannel(
            name="Ambience Session",
            handle="@OpenLofiStudio",
            url="https://www.youtube.com/@OpenLofiStudio",
        ),
        limits=Limits(
            max_candidates_per_run=15,
            max_comments_per_run=5,
            max_comments_per_day=5,
            max_comments_per_week=8,
            min_days_between_same_channel=14,
            max_video_age_days=14,
        ),
        discovery=Discovery(
            enabled=True,
            max_results_per_query=10,
            queries=("coding ambience",),
            excluded_title_terms=("sad song",),
        ),
        comment_rules=CommentRules(
            language="en",
            min_length=120,
            max_length=350,
            max_emojis=2,
            max_links=1,
            forbidden_phrases=("sub4sub", "check out my channel"),
        ),
        soft_mention_templates=(
            "Building long dev focus sessions over at {channelName} if that is your vibe.",
            "Also crafting immersive dev focus sessions at {channelName} for deep work days.",
        ),
        target_channels=[
            TargetChannel(
                handle="@thesoundyouneed1",
                name="TheSoundYouNeed",
                channel_id="UC123",
                priority=1,
                comment_angle="long-form soundscape",
            )
        ],
        config_path=str(ROOT / "assets/youtube-outreach-config.json"),
    )


def sample_candidate(
    video_id: str = "vid1",
    channel_id: str = "UC123",
    title: str = "8 Hours Rain Sounds for Deep Focus",
    days_ago: int = 2,
) -> VideoCandidate:
    published = datetime.now(UTC) - timedelta(days=days_ago)
    return VideoCandidate(
        video_id=video_id,
        title=title,
        channel_id=channel_id,
        channel_name="TheSoundYouNeed",
        published_at=published,
        url=f"https://www.youtube.com/watch?v={video_id}",
    )


class ConfigTests(unittest.TestCase):
    def test_load_outreach_config(self) -> None:
        config = load_outreach_config(ROOT / "assets/youtube-outreach-config.json")
        self.assertEqual(config.our_channel.name, "Ambience Session")
        self.assertEqual(len(config.target_channels), 5)
        self.assertEqual(config.limits.max_comments_per_run, 10)
        self.assertEqual(config.limits.max_comments_per_day, 20)
        self.assertEqual(config.limits.max_comments_per_week, 200)

    def test_save_channel_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            source = ROOT / "assets/youtube-outreach-config.json"
            config_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            channels = [
                TargetChannel(
                    handle="@thesoundyouneed1",
                    name="TheSoundYouNeed",
                    channel_id="UCresolved",
                    priority=1,
                    comment_angle="test",
                )
            ]
            save_channel_ids(config_path, channels)
            raw = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(raw["targetChannels"][0]["channelId"], "UCresolved")


class LogStoreTests(unittest.TestCase):
    def test_log_roundtrip_and_dedup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "log.json"
            entry = CommentEntry(
                video_id="vid1",
                channel_id="UC123",
                comment_id="cmt1",
                posted_at=datetime.now(UTC).isoformat(),
                text="sample",
                channel_name="TheSoundYouNeed",
                video_title="Rain",
            )
            append_log_entry(log_path, entry)
            append_log_entry(log_path, entry)
            entries = load_log(log_path)
            self.assertEqual(len(entries), 1)
            self.assertTrue(has_commented_on_video(entries, "vid1"))

    def test_count_comments_since(self) -> None:
        now = datetime.now(UTC)
        entries = [
            CommentEntry("v1", "c1", "cm1", (now - timedelta(days=1)).isoformat(), "a", "n", "t"),
            CommentEntry("v2", "c2", "cm2", (now - timedelta(days=10)).isoformat(), "b", "n", "t"),
        ]
        self.assertEqual(count_comments_since(entries, now - timedelta(days=7)), 1)


class FilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.limits = sample_config().limits
        self.now = datetime(2026, 7, 11, tzinfo=UTC)

    def test_is_video_too_old(self) -> None:
        recent = datetime(2026, 7, 10, tzinfo=UTC)
        old = datetime(2026, 6, 20, tzinfo=UTC)
        self.assertFalse(is_video_too_old(recent, 14, self.now))
        self.assertTrue(is_video_too_old(old, 14, self.now))

    def test_weekly_limit_reached(self) -> None:
        entries = [
            CommentEntry(
                f"v{i}",
                "UC123",
                f"c{i}",
                (self.now - timedelta(days=1)).isoformat(),
                "text",
                "name",
                "title",
            )
            for i in range(8)
        ]
        self.assertTrue(weekly_limit_reached(entries, 8, self.now))

    def test_channel_cooldown(self) -> None:
        entries = [
            CommentEntry(
                "v1",
                "UC123",
                "c1",
                (self.now - timedelta(days=3)).isoformat(),
                "text",
                "name",
                "title",
            )
        ]
        self.assertTrue(is_channel_on_cooldown(entries, "UC123", 14, self.now))
        self.assertFalse(is_channel_on_cooldown(entries, "UC999", 14, self.now))

    def test_filter_candidates(self) -> None:
        candidates = [
            sample_candidate("v1", "UC123"),
            sample_candidate("v2", "UC123"),
            sample_candidate("v3", "UC456", days_ago=2),
        ]
        entries = [
            CommentEntry(
                "old",
                "UC123",
                "c1",
                (self.now - timedelta(days=3)).isoformat(),
                "text",
                "TheSoundYouNeed",
                "Rain",
            )
        ]
        filtered = filter_candidates(candidates, entries, self.limits, self.now)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].video_id, "v3")


class CommentGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = sample_config()
        self.candidate = sample_candidate()

    def test_infer_mood(self) -> None:
        self.assertEqual(infer_mood("Rain on window 8 hours"), "rain")
        self.assertEqual(infer_mood("Coffee shop morning jazz"), "coffee")
        self.assertEqual(infer_mood("Neon cyberpunk night"), "cyberpunk")
        self.assertEqual(infer_mood("Deep orbit nebula"), "space")
        self.assertEqual(infer_mood("Random ambience"), "generic")

    def test_validate_comment_rules(self) -> None:
        valid = (
            "The rain layer sits perfectly under everything without stealing focus during a long refactor. "
            "Building long dev focus sessions over at Ambience Session if that is your vibe."
        )
        self.assertEqual(validate_comment(valid, self.config.comment_rules, self.config.our_channel), [])

        invalid = "Nice video!"
        errors = validate_comment(invalid, self.config.comment_rules, self.config.our_channel)
        self.assertTrue(any("too short" in error for error in errors))
        self.assertTrue(any("missing soft mention" in error for error in errors))

    def test_rejects_em_dash_in_comment(self) -> None:
        with_dash = (
            "The rain layer sits perfectly under everything without stealing focus — perfect for coding. "
            "Building long dev focus sessions over at Ambience Session if that is your vibe."
        )
        errors = validate_comment(with_dash, self.config.comment_rules, self.config.our_channel)
        self.assertTrue(any("forbidden dash" in error for error in errors))

    def test_sanitize_and_generate_removes_dashes(self) -> None:
        from youtube_outreach.comment_generator import sanitize_comment_dashes

        cleaned = sanitize_comment_dashes(
            "Calm rain texture — perfect for a long refactor session at night."
        )
        self.assertNotIn("\u2014", cleaned)
        self.assertIn(",", cleaned)

        class MockGenerator:
            def generate(self, prompt: str) -> str:
                return (
                    "The rain texture here is perfect for an all-night deploy session — no distraction. "
                    "Building long dev focus sessions over at Ambience Session if that is your vibe."
                )

        comment = generate_comment(
            self.candidate,
            "rain ambience",
            self.config,
            generator=MockGenerator(),
        )
        self.assertNotIn("\u2014", comment)
        self.assertNotIn("\u2013", comment)
        self.assertIn("Ambience Session", comment)

    def test_build_fallback_comment(self) -> None:
        comment = build_fallback_comment(self.candidate, "rain ambience", self.config)
        self.assertIn("Ambience Session", comment)
        self.assertGreaterEqual(len(comment), self.config.comment_rules.min_length)

    def test_generate_comment_with_mock_llm(self) -> None:
        class MockGenerator:
            def generate(self, prompt: str) -> str:
                return (
                    "The rain texture here is perfect for an all-night deploy session without distraction. "
                    "Building long dev focus sessions over at Ambience Session if that is your vibe."
                )

        comment = generate_comment(
            self.candidate,
            "rain ambience",
            self.config,
            generator=MockGenerator(),
        )
        self.assertIn("Ambience Session", comment)


class YouTubeClientTests(unittest.TestCase):
    def test_resolve_channel_id_by_handle(self) -> None:
        service = MagicMock()
        service.channels.return_value.list.return_value.execute.return_value = {
            "items": [{"id": "UCresolved"}]
        }
        client = YouTubeClient(service)
        self.assertEqual(client.resolve_channel_id("@thesoundyouneed1"), "UCresolved")

    def test_resolve_channel_id_fallback_search(self) -> None:
        service = MagicMock()
        channels_list = service.channels.return_value.list.return_value
        channels_list.execute.return_value = {"items": []}
        search_list = service.search.return_value.list.return_value
        search_list.execute.return_value = {
            "items": [{"snippet": {"channelId": "UCsearch"}}]
        }
        client = YouTubeClient(service)
        self.assertEqual(client.resolve_channel_id("@missing"), "UCsearch")

    def test_fetch_recent_videos(self) -> None:
        service = MagicMock()
        channels_list = service.channels.return_value.list.return_value
        channels_list.execute.return_value = {
            "items": [{"contentDetails": {"relatedPlaylists": {"uploads": "PLuploads"}}}]
        }
        playlist_list = service.playlistItems.return_value.list.return_value
        playlist_list.execute.return_value = {
            "items": [
                {
                    "snippet": {
                        "title": "Rain Focus 8h",
                        "publishedAt": "2026-07-10T12:00:00Z",
                    },
                    "contentDetails": {"videoId": "abc123"},
                }
            ]
        }
        client = YouTubeClient(service)
        channel = TargetChannel(
            handle="@test",
            name="Test",
            channel_id="UC123",
            priority=1,
            comment_angle="focus",
        )
        videos = client.fetch_recent_videos(channel, max_results=1)
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0].video_id, "abc123")

    def test_search_recent_videos(self) -> None:
        service = MagicMock()
        search_list = service.search.return_value.list.return_value
        search_list.execute.return_value = {
            "items": [
                {
                    "id": {"videoId": "search123"},
                    "snippet": {
                        "title": "Coding Ambience for Deep Work",
                        "channelId": "UCsearch",
                        "channelTitle": "Focus Channel",
                        "publishedAt": "2026-07-10T12:00:00Z",
                    },
                }
            ]
        }
        client = YouTubeClient(service)
        videos = client.search_recent_videos(
            "coding ambience",
            published_after=datetime(2026, 7, 1, tzinfo=UTC),
            max_results=10,
        )
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0].channel_name, "Focus Channel")
        service.search.return_value.list.assert_called_once_with(
            part="snippet",
            q="coding ambience",
            type="video",
            order="date",
            publishedAfter="2026-07-01T00:00:00Z",
            videoDuration="long",
            relevanceLanguage="en",
            maxResults=10,
        )

    def test_post_comment(self) -> None:
        service = MagicMock()
        insert = service.commentThreads.return_value.insert.return_value
        insert.execute.return_value = {"id": "thread123"}
        client = YouTubeClient(service)
        comment_id = client.post_comment("vid1", "Hello world")
        self.assertEqual(comment_id, "thread123")

    def test_resolve_all_channel_ids(self) -> None:
        service = MagicMock()
        service.channels.return_value.list.return_value.execute.return_value = {
            "items": [{"id": "UCnew"}]
        }
        client = YouTubeClient(service)
        channels = [
            TargetChannel("@test", "Test", None, 1, "angle"),
        ]
        resolved = resolve_all_channel_ids(client, channels)
        self.assertEqual(resolved[0].channel_id, "UCnew")

    def test_resolve_channel_id_not_found(self) -> None:
        service = MagicMock()
        service.channels.return_value.list.return_value.execute.return_value = {"items": []}
        service.search.return_value.list.return_value.execute.return_value = {"items": []}
        client = YouTubeClient(service)
        with self.assertRaises(ValueError):
            client.resolve_channel_id("@missing")

    def test_save_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from google.oauth2.credentials import Credentials

            token_path = Path(tmp) / "token.json"
            credentials = Credentials(token="abc", refresh_token="ref")
            save_credentials(token_path, credentials)
            self.assertTrue(token_path.exists())

    def test_build_client_secrets_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "secrets.json"
            build_client_secrets_file("id", "secret", path)
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(raw["installed"]["client_id"], "id")

    def test_fetch_recent_videos_missing_channel(self) -> None:
        service = MagicMock()
        service.channels.return_value.list.return_value.execute.return_value = {"items": []}
        client = YouTubeClient(service)
        channel = TargetChannel("@test", "Test", "UCmissing", 1, "angle")
        with self.assertRaises(ValueError):
            client.fetch_recent_videos(channel)

    def test_fetch_recent_videos_requires_channel_id(self) -> None:
        service = MagicMock()
        client = YouTubeClient(service)
        channel = TargetChannel("@test", "Test", None, 1, "angle")
        with self.assertRaises(ValueError):
            client.fetch_recent_videos(channel)

    def test_load_credentials_missing_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_path = Path(tmp) / "missing.json"
            secrets_path = Path(tmp) / "secrets.json"
            build_client_secrets_file("id", "secret", secrets_path)
            with self.assertRaises(FileNotFoundError):
                load_credentials(token_path, secrets_path)

    def test_load_credentials_valid_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            token_path = Path(tmp) / "token.json"
            secrets_path = Path(tmp) / "secrets.json"
            build_client_secrets_file("id", "secret", secrets_path)
            token_path.write_text(
                json.dumps(
                    {
                        "token": "abc",
                        "refresh_token": "refresh",
                        "client_id": "id",
                        "client_secret": "secret",
                        "scopes": ["https://www.googleapis.com/auth/youtube.force-ssl"],
                        "expiry": "2099-01-01T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )
            loaded = load_credentials(token_path, secrets_path)
            self.assertEqual(loaded.token, "abc")


if __name__ == "__main__":
    unittest.main()
