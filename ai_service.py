import os
import json
import re
import logging
from typing import Optional
from config import settings


logger = logging.getLogger(__name__)


class NvidiaAIContent:
    def __init__(self, title: str, caption: str, hashtags: list[str]):
        self.title = title
        self.caption = caption
        self.hashtags = hashtags

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "caption": self.caption,
            "hashtags": self.hashtags,
        }


class NvidiaAIService:
    API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
    DEFAULT_MODEL = "google/gemma-3n-e4b-it"

    def __init__(self):
        self.api_key = settings.nvidia_api_key
        if not self.api_key:
            logger.warning("NVIDIA_API_KEY not set. AI content generation will use fallback mode.")

    def generate_content(
        self,
        filename: str,
        topic: str = "motivation",
        audience: str = "Indian audience",
        style: str = "energetic",
    ) -> NvidiaAIContent:
        prompt = self._build_prompt(filename, topic, audience, style)

        if not self.api_key:
            logger.warning("Using fallback content generation")
            return self._generate_fallback(filename)

        try:
            return self._call_nvidia_api(prompt)
        except Exception as e:
            logger.error(f"NVIDIA API error: {e}. Using fallback.")
            return self._generate_fallback(filename)

    def _build_prompt(self, filename: str, topic: str, audience: str, style: str) -> str:
        return f"""You are a viral YouTube Shorts content creator. Generate engaging content for the following reel.

Filename: {filename}
Topic: {topic}
Target Audience: {audience}
Style: {style}

Generate exactly this format:
TITLE: [1 viral YouTube Shorts title with emoji]
CAPTION: [Short engaging caption, 2-3 lines max]
HASHTAGS: [10 trending hashtags separated by spaces, include #shorts]

Start now."""

    def _call_nvidia_api(self, prompt: str) -> NvidiaAIContent:
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.DEFAULT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "max_tokens": 300,
        }

        response = requests.post(self.API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return self._parse_response(content)

    def _parse_response(self, content: str) -> NvidiaAIContent:
        title = ""
        caption = ""
        hashtags = []

        title_match = re.search(r"TITLE:\s*(.+?)(?=CAPTION:|$)", content, re.DOTALL | re.IGNORECASE)
        caption_match = re.search(r"CAPTION:\s*(.+?)(?=HASHTAGS:|$)", content, re.DOTALL | re.IGNORECASE)
        hashtags_match = re.search(r"HASHTAGS:\s*(.+?)$", content, re.DOTALL | re.IGNORECASE)

        if title_match:
            title = title_match.group(1).strip()
        if caption_match:
            caption = caption_match.group(1).strip()
        if hashtags_match:
            tags_text = hashtags_match.group(1).strip()
            hashtags = [t.strip() for t in re.findall(r"#\w+", tags_text)]

        if not title:
            title = "Watch This! 🔥"
        if not caption:
            caption = "Incredible content you don't want to miss!"
        if not hashtags:
            hashtags = ["#shorts", "#viral", "#trending", "#fyp", "#explore", "#motivation", "#success", "#india", "#reels", "#trending"]

        return NvidiaAIContent(title=title, caption=caption, hashtags=hashtags)

    def _generate_fallback(self, filename: str) -> NvidiaAIContent:
        seq_match = re.search(r"ota(\d+)", filename, re.IGNORECASE)
        seq_num = seq_match.group(1) if seq_match else "1"

        title = f"Episode {seq_num} Drops Now 🔥"
        caption = f"Part {seq_num} of the series. Don't forget to like and subscribe!"
        hashtags = ["#shorts", "#viral", "#trending", "#fyp", "#explore", "#episode", "#series", "#new", "#reels", "#subscribe"]

        return NvidiaAIContent(title=title, caption=caption, hashtags=hashtags)


ai_service = NvidiaAIService()