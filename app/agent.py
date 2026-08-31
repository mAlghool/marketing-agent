"""Content generation agent: turns a campaign brief into platform-ready captions."""

from __future__ import annotations

import json
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.config import get_settings
from app.models import Campaign, Platform

PLATFORM_GUIDELINES: dict[Platform, str] = {
    Platform.facebook: (
        "Facebook page post: 2-4 short sentences, conversational, may include a link and a "
        "clear call to action. Up to 3 hashtags."
    ),
    Platform.instagram: (
        "Instagram caption: hook in the first line, short lines, emojis allowed, "
        "8-12 relevant hashtags at the end."
    ),
    Platform.tiktok: (
        "TikTok caption: max 150 characters, punchy hook, trend-aware, 3-5 hashtags."
    ),
}

SYSTEM_PROMPT = (
    "You are a senior social media marketer. You write native-feeling posts for each platform, "
    "never generic filler, and you always respect the requested language and brand voice. "
    "Return strict JSON only."
)


@dataclass
class GeneratedPost:
    platform: Platform
    caption: str


def build_prompt(campaign: Campaign, platforms: list[Platform], count_per_platform: int) -> str:
    settings = get_settings()
    voice = campaign.brand_voice or settings.brand_voice
    guidelines = "\n".join(f"- {p.value}: {PLATFORM_GUIDELINES[p]}" for p in platforms)
    return (
        f"Brand: {settings.brand_name}\n"
        f"Campaign: {campaign.name}\n"
        f"Goal: {campaign.goal}\n"
        f"Audience: {campaign.audience or 'general audience'}\n"
        f"Brand voice: {voice}\n"
        f"Language: {campaign.language or settings.brand_language}\n"
        f"Preferred hashtags: {campaign.hashtags or 'none'}\n\n"
        f"Write {count_per_platform} distinct post(s) for each of these platforms:\n"
        f"{guidelines}\n\n"
        'Respond as JSON: {"posts": [{"platform": "facebook", "caption": "..."}]}'
    )


class ContentAgent:
    def __init__(self, client: AsyncOpenAI | None = None) -> None:
        settings = get_settings()
        self._client = client or AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    async def generate(
        self,
        campaign: Campaign,
        platforms: list[Platform],
        count_per_platform: int = 1,
    ) -> list[GeneratedPost]:
        response = await self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(campaign, platforms, count_per_platform)},
            ],
        )
        return parse_generation(response.choices[0].message.content or "{}", platforms)


def parse_generation(raw: str, allowed: list[Platform]) -> list[GeneratedPost]:
    data = json.loads(raw)
    posts: list[GeneratedPost] = []
    for item in data.get("posts", []):
        try:
            platform = Platform(item["platform"])
        except (KeyError, ValueError):
            continue
        caption = (item.get("caption") or "").strip()
        if platform in allowed and caption:
            posts.append(GeneratedPost(platform=platform, caption=caption))
    return posts
