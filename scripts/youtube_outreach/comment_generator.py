from __future__ import annotations

import re
from typing import Protocol

from youtube_outreach.models import CommentRules, OurChannel, OutreachConfig, VideoCandidate

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F600-\U0001F64F"
    "]+",
    flags=re.UNICODE,
)
URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
FORBIDDEN_DASH_CHARS = ("\u2014", "\u2013", "\u2015")
FORBIDDEN_DASH_PATTERN = re.compile(r"[\u2014\u2013\u2015]")
MOOD_KEYWORDS: dict[str, tuple[str, ...]] = {
    "rain": ("rain", "storm", "thunder", "wet", "drizzle"),
    "coffee": ("coffee", "cafe", "café", "espresso", "latte"),
    "cyberpunk": ("cyberpunk", "neon", "blade runner", "synthwave", "2077"),
    "space": ("space", "orbit", "mars", "galaxy", "nebula", "lunar", "iss"),
    "cabin": ("cabin", "fireplace", "forest", "mountain", "snow", "cozy"),
    "study": ("study", "focus", "deep work", "concentration", "lofi", "lo-fi"),
}

FALLBACK_OPENERS: dict[str, tuple[str, ...]] = {
    "rain": (
        "The rain layer sits perfectly under everything without stealing focus.",
        "That window rain texture is exactly what a long coding session needs.",
    ),
    "coffee": (
        "The warm café mood here is perfect for a slow morning refactor.",
        "Love how the coffee-shop atmosphere stays calm without going sleepy.",
    ),
    "cyberpunk": (
        "The neon mood is sharp but still usable for a full night of coding.",
        "This cyberpunk atmosphere hits the late-night deploy energy perfectly.",
    ),
    "space": (
        "The quiet space ambience makes deep work feel almost weightless.",
        "Something about the orbital stillness keeps my focus locked for hours.",
    ),
    "cabin": (
        "The cabin warmth and outdoor hush are perfect for off-grid coding days.",
        "Fireplace plus silence is an underrated combo for long debugging sessions.",
    ),
    "study": (
        "This focus mix stays out of the way while still giving the session some shape.",
        "Exactly the kind of background that helps you stay in flow without noticing it.",
    ),
    "generic": (
        "This atmosphere lands perfectly for a long work session in the background.",
        "The soundscape here is the kind you can leave running for an entire sprint.",
    ),
}


class TextGenerator(Protocol):
    def generate(self, prompt: str) -> str: ...


def infer_mood(title: str) -> str:
    lowered = title.lower()
    for mood, keywords in MOOD_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return mood
    return "generic"


def count_emojis(text: str) -> int:
    return len(EMOJI_PATTERN.findall(text))


def count_links(text: str) -> int:
    return len(URL_PATTERN.findall(text))


def sanitize_comment_dashes(text: str) -> str:
    cleaned = text
    for dash in FORBIDDEN_DASH_CHARS:
        cleaned = re.sub(rf"\s*{re.escape(dash)}\s*", ", ", cleaned)
    cleaned = re.sub(r",\s*,+", ", ", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip(" ,")


def has_forbidden_dash(text: str) -> bool:
    return FORBIDDEN_DASH_PATTERN.search(text) is not None


def has_excessive_caps(text: str) -> bool:
    letters = [char for char in text if char.isalpha()]
    if len(letters) < 20:
        return False
    upper = sum(1 for char in letters if char.isupper())
    return upper / len(letters) > 0.4


def contains_soft_mention(text: str, our_channel: OurChannel) -> bool:
    lowered = text.lower()
    return our_channel.name.lower() in lowered or our_channel.url.lower() in lowered


def validate_comment(text: str, rules: CommentRules, our_channel: OurChannel) -> list[str]:
    errors: list[str] = []
    stripped = text.strip()
    if len(stripped) < rules.min_length:
        errors.append(f"too short ({len(stripped)} chars, min {rules.min_length})")
    if len(stripped) > rules.max_length:
        errors.append(f"too long ({len(stripped)} chars, max {rules.max_length})")
    if count_emojis(stripped) > rules.max_emojis:
        errors.append(f"too many emojis (max {rules.max_emojis})")
    if count_links(stripped) > rules.max_links:
        errors.append(f"too many links (max {rules.max_links})")
    if has_excessive_caps(stripped):
        errors.append("excessive caps")
    if has_forbidden_dash(stripped):
        errors.append("forbidden dash character (use comma instead of —)")
    lowered = stripped.lower()
    for phrase in rules.forbidden_phrases:
        if phrase.lower() in lowered:
            errors.append(f"forbidden phrase: {phrase}")
    if not contains_soft_mention(stripped, our_channel):
        errors.append("missing soft mention of our channel")
    return errors


def pick_soft_mention(config: OutreachConfig, seed: int) -> str:
    template = config.soft_mention_templates[seed % len(config.soft_mention_templates)]
    return template.format(
        channelName=config.our_channel.name,
        channelUrl=config.our_channel.url,
    )


def build_fallback_comment(
    candidate: VideoCandidate,
    channel_angle: str,
    config: OutreachConfig,
    seed: int = 0,
) -> str:
    mood = infer_mood(candidate.title)
    openers = FALLBACK_OPENERS.get(mood, FALLBACK_OPENERS["generic"])
    opener = openers[seed % len(openers)]
    mention = pick_soft_mention(config, seed + 1)
    detail = f"Came here from the {channel_angle} niche and this one delivers."
    return f"{opener} {detail} {mention}"


def build_llm_prompt(
    candidate: VideoCandidate,
    channel_angle: str,
    config: OutreachConfig,
) -> str:
    mention = pick_soft_mention(config, hash(candidate.video_id) % len(config.soft_mention_templates))
    return (
        "Write one YouTube comment in English for an ambience/focus video.\n"
        f"Video title: {candidate.title}\n"
        f"Channel: {candidate.channel_name}\n"
        f"Angle: {channel_angle}\n"
        f"Our channel: {config.our_channel.name} ({config.our_channel.url})\n"
        "Rules:\n"
        "- 1 to 3 calm sentences, no hype, no clickbait\n"
        "- Reference something specific from the title or mood\n"
        "- Must include this soft mention verbatim or very close: "
        f"\"{mention}\"\n"
        f"- Between {config.comment_rules.min_length} and {config.comment_rules.max_length} characters\n"
        f"- At most {config.comment_rules.max_emojis} emoji\n"
        "- Never use em dashes or en dashes (—, –, ―); use a comma or period instead\n"
        "- No sub4sub, no begging for subs, no multiple links\n"
        "- Output only the comment text, nothing else"
    )


def generate_comment(
    candidate: VideoCandidate,
    channel_angle: str,
    config: OutreachConfig,
    generator: TextGenerator | None = None,
    max_attempts: int = 3,
) -> str:
    for attempt in range(max_attempts):
        if generator is not None:
            prompt = build_llm_prompt(candidate, channel_angle, config)
            text = generator.generate(prompt).strip().strip('"')
        else:
            text = build_fallback_comment(candidate, channel_angle, config, seed=attempt)
        text = sanitize_comment_dashes(text)
        errors = validate_comment(text, config.comment_rules, config.our_channel)
        if not errors:
            return text
    return sanitize_comment_dashes(
        build_fallback_comment(candidate, channel_angle, config, seed=max_attempts)
    )
