import json

from app.agent import build_prompt, parse_generation
from app.models import Campaign, Platform


def test_parse_generation_filters_unknown_and_empty():
    raw = json.dumps(
        {
            "posts": [
                {"platform": "facebook", "caption": "مرحبا"},
                {"platform": "instagram", "caption": "  "},
                {"platform": "threads", "caption": "nope"},
                {"platform": "tiktok", "caption": "hook"},
            ]
        }
    )
    posts = parse_generation(raw, [Platform.facebook, Platform.instagram])
    assert [(p.platform, p.caption) for p in posts] == [(Platform.facebook, "مرحبا")]


def test_build_prompt_includes_campaign_context():
    campaign = Campaign(name="Launch", goal="signups", audience="SMBs", language="ar")
    prompt = build_prompt(campaign, [Platform.tiktok], 2)
    assert "Launch" in prompt and "signups" in prompt and "SMBs" in prompt
    assert "Write 2 distinct post(s)" in prompt
    assert "tiktok" in prompt
