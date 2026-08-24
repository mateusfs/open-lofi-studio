from __future__ import annotations

import json
import os
from html import unescape
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from youtube_outreach.models import TargetChannel, VideoCandidate

SCOPES = ("https://www.googleapis.com/auth/youtube.force-ssl",)


class YouTubeClient:
    def __init__(self, service: Any) -> None:
        self._service = service

    @classmethod
    def from_credentials(cls, token_path: Path, client_secrets_path: Path) -> YouTubeClient:
        credentials = load_credentials(token_path, client_secrets_path)
        service = build("youtube", "v3", credentials=credentials, cache_discovery=False)
        return cls(service)

    def resolve_channel_id(self, handle: str) -> str:
        normalized = handle.lstrip("@")
        try:
            response = (
                self._service.channels()
                .list(part="id", forHandle=normalized)
                .execute()
            )
            items = response.get("items", [])
            if items:
                return items[0]["id"]
        except HttpError:
            pass

        search = (
            self._service.search()
            .list(part="snippet", q=handle, type="channel", maxResults=1)
            .execute()
        )
        items = search.get("items", [])
        if not items:
            raise ValueError(f"Could not resolve channel handle: {handle}")
        return items[0]["snippet"]["channelId"]

    def fetch_recent_videos(
        self,
        channel: TargetChannel,
        max_results: int = 5,
    ) -> list[VideoCandidate]:
        if not channel.channel_id:
            raise ValueError(f"Channel ID missing for {channel.handle}")
        uploads_playlist = self._fetch_uploads_playlist_id(channel.channel_id)
        playlist_items = (
            self._service.playlistItems()
            .list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist,
                maxResults=max_results,
            )
            .execute()
        )
        candidates: list[VideoCandidate] = []
        for item in playlist_items.get("items", []):
            snippet = item["snippet"]
            video_id = item["contentDetails"]["videoId"]
            published_raw = snippet["publishedAt"]
            published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
            candidates.append(
                VideoCandidate(
                    video_id=video_id,
                    title=unescape(snippet["title"]),
                    channel_id=channel.channel_id,
                    channel_name=channel.name,
                    published_at=published_at,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                )
            )
        return candidates

    def search_recent_videos(
        self,
        query: str,
        published_after: datetime,
        max_results: int = 10,
    ) -> list[VideoCandidate]:
        response = (
            self._service.search()
            .list(
                part="snippet",
                q=query,
                type="video",
                order="date",
                publishedAfter=published_after.astimezone(UTC).isoformat().replace(
                    "+00:00", "Z"
                ),
                videoDuration="long",
                relevanceLanguage="en",
                maxResults=max_results,
            )
            .execute()
        )
        candidates: list[VideoCandidate] = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            video_id = item["id"]["videoId"]
            candidates.append(
                VideoCandidate(
                    video_id=video_id,
                    title=unescape(snippet["title"]),
                    channel_id=snippet["channelId"],
                    channel_name=unescape(snippet["channelTitle"]),
                    published_at=datetime.fromisoformat(
                        snippet["publishedAt"].replace("Z", "+00:00")
                    ),
                    url=f"https://www.youtube.com/watch?v={video_id}",
                )
            )
        return candidates

    def post_comment(self, video_id: str, text: str) -> str:
        body = {
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": text,
                    }
                },
            }
        }
        response = self._service.commentThreads().insert(part="snippet", body=body).execute()
        return response["id"]

    def _fetch_uploads_playlist_id(self, channel_id: str) -> str:
        response = (
            self._service.channels()
            .list(part="contentDetails", id=channel_id)
            .execute()
        )
        items = response.get("items", [])
        if not items:
            raise ValueError(f"Channel not found: {channel_id}")
        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def load_credentials(token_path: Path, client_secrets_path: Path) -> Credentials:
    credentials: Credentials | None = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        save_credentials(token_path, credentials)
    if credentials and credentials.valid:
        return credentials
    raise FileNotFoundError(
        f"Missing or invalid OAuth token at {token_path}. Run with --auth first."
    )


def run_oauth_flow(token_path: Path, client_secrets_path: Path) -> Credentials:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
    credentials = flow.run_local_server(port=0)
    save_credentials(token_path, credentials)
    return credentials


def save_credentials(token_path: Path, credentials: Credentials) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")


def build_client_secrets_file(client_id: str, client_secret: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def resolve_all_channel_ids(
    client: YouTubeClient,
    channels: list[TargetChannel],
) -> list[TargetChannel]:
    resolved: list[TargetChannel] = []
    for channel in channels:
        channel_id = channel.channel_id or client.resolve_channel_id(channel.handle)
        resolved.append(
            TargetChannel(
                handle=channel.handle,
                name=channel.name,
                channel_id=channel_id,
                priority=channel.priority,
                comment_angle=channel.comment_angle,
            )
        )
    return resolved
