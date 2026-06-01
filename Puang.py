import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import random
import time
import datetime
import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import shutil
import json
import math
import base64
import io
import re
import xml.etree.ElementTree as ET
from array import array
from queue import Empty, Queue
import aiohttp
from discord.ext import tasks
from mcrcon import MCRcon
# --- [수정: 개인별 맞춤 TTS 및 자동 설치 설정] ---
import subprocess
import sys

# edge-tts 자동 설치 로직
try:
    import edge_tts
except ImportError:
    print("🔄 edge-tts가 없습니다. 자동으로 설치합니다...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "edge-tts"])
    import edge_tts
    print("✅ edge-tts 설치 완료!")

from gtts import gTTS
import uuid
import os
import json

TTS_FILE = "tts_settings.json"
VOLUME_FILE = "volume_settings.json"
AI_SETTINGS_FILE = "ai_settings.json"
AI_PROVIDERS_FILE = "ai_providers.json"
AI_MODELS_FILE = "ai_models.json"
AI_USAGE_LOG_FILE = "ai_usage_log.jsonl"
AI_SHORT_MEMORY_FILE = "ai_short_memory.json"
AI_LONG_MEMORY_FILE = "ai_long_memory.json"

AI_DEFAULT_PROVIDER_ID = "local-ollama"
AI_DEFAULT_MODEL = "local-fast"
AI_DEFAULT_FALLBACK_TEXT_MODEL = "local-tiny"
AI_DEFAULT_FALLBACK_VISION_MODEL = "local-vision"
AI_DEFAULT_DOCUMENT_MODEL = "local-fast"
AI_DEFAULT_FALLBACK_POLICY = "safe_degrade"
AI_DEFAULT_BASE_URL = "http://127.0.0.1:11434"
AI_DEFAULT_MAX_TOKENS = 2048
AI_LONGFORM_MAX_TOKENS = 4096
AI_SHORT_MEMORY_LIMIT = 20
AI_LONG_MEMORY_LIMIT = 500
AI_MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024
DISCORD_MESSAGE_CONTENT_LIMIT = 2000
DISCORD_SAFE_MESSAGE_LIMIT = 1900
AI_REPLY_INLINE_LIMIT = DISCORD_SAFE_MESSAGE_LIMIT
AI_REPLY_PREVIEW_LIMIT = 1000
AI_REPLY_FILE_BYTE_LIMIT = 8 * 1024 * 1024
AI_ALLOWED_TEXT_EXTENSIONS = {".txt", ".md", ".py", ".js", ".ts", ".json", ".csv", ".log", ".yml", ".yaml"}
AI_ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".docx"}
AI_ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
AI_SYSTEM_PROMPT = (
    "너는 디스코드 서버의 로컬 AI 비서 '푸앙봇'이다. "
    "한국어로 자연스럽고 간결하게 답하되, 사용자가 요구하면 자세히 설명한다. "
    "최근 대화 기억을 참고하고, 첨부 문서나 이미지 정보가 있으면 그 내용을 근거로 답한다."
)

def load_tts():
    try:
        with open(TTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_tts(data):
    with open(TTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_volume_settings():
    try:
        with open(VOLUME_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_volume_settings(data):
    with open(VOLUME_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def save_guild_volume_settings(guild_id, state):
    data = load_volume_settings()
    data[str(guild_id)] = {
        "music_volume": state.volume,
        "tts_duck_volume": state.tts_duck_volume
    }
    save_volume_settings(data)

def load_json_file(path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        print(f"⚠️ {path} 파일을 읽을 수 없어 기본값을 사용합니다.")
        return default

def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_default_ai_providers():
    return {
        "providers": {
            "local-ollama": {
                "type": "ollama",
                "enabled": True,
                "base_url": AI_DEFAULT_BASE_URL,
                "privacy": "local",
                "api_key_env": None,
                "timeout": 120
            },
            "openrouter-main": {
                "type": "openai_compatible",
                "enabled": False,
                "base_url": "https://openrouter.ai/api/v1",
                "privacy": "external",
                "api_key_env": "OPENROUTER_API_KEY",
                "timeout": 180
            },
            "openai-main": {
                "type": "openai_compatible",
                "enabled": False,
                "base_url": "https://api.openai.com/v1",
                "privacy": "external",
                "api_key_env": "OPENAI_API_KEY",
                "timeout": 180
            },
            "lmstudio-local": {
                "type": "openai_compatible",
                "enabled": False,
                "base_url": "http://127.0.0.1:1234/v1",
                "privacy": "local",
                "api_key_env": None,
                "timeout": 180
            }
        }
    }

def get_ai_providers():
    defaults = get_default_ai_providers()
    data = load_json_file(AI_PROVIDERS_FILE, None)
    if not isinstance(data, dict):
        return defaults

    providers = defaults["providers"].copy()
    custom_providers = data.get("providers", {})
    if isinstance(custom_providers, dict):
        for provider_id, provider in custom_providers.items():
            if isinstance(provider, dict):
                merged = providers.get(provider_id, {}).copy()
                merged.update(provider)
                providers[provider_id] = merged
    data["providers"] = providers
    return data

def get_default_ai_models():
    return {
        "profiles": {
            "local-tiny": {
                "label": "로컬 최후 백업",
                "provider": "local-ollama",
                "model": "qwen2.5:0.5b",
                "capabilities": ["text"],
                "privacy": "local",
                "selectable": True,
                "visible": True,
                "group": "local",
                "cost_tier": "free",
                "context": 4096,
                "timeout": 90,
                "note": "8GB RAM 환경의 최후 텍스트 백업용"
            },
            "local-fast": {
                "label": "로컬 빠른 대화",
                "provider": "local-ollama",
                "model": "qwen2.5:1.5b",
                "capabilities": ["text"],
                "privacy": "local",
                "selectable": True,
                "visible": True,
                "group": "local",
                "cost_tier": "free",
                "context": 8192,
                "timeout": 120,
                "fallbacks": ["local-tiny"],
                "note": "저사양 PC 기본 대화 모델"
            },
            "local-gemma4": {
                "label": "Gemma 4 8B",
                "provider": "local-ollama",
                "model": "gemma4:latest",
                "capabilities": ["text", "image"],
                "privacy": "local",
                "selectable": True,
                "visible": True,
                "group": "local",
                "cost_tier": "free",
                "context": 8192,
                "timeout": 300,
                "max_tokens": AI_LONGFORM_MAX_TOKENS,
                "fallbacks": ["local-fast", "local-tiny"],
                "note": "16GB RAM 환경의 고품질 로컬 기본 모델 후보"
            },
            "local-korean": {
                "label": "로컬 한국어 품질",
                "provider": "local-ollama",
                "model": "exaone3.5:2.4b",
                "capabilities": ["text"],
                "privacy": "local",
                "selectable": True,
                "visible": True,
                "group": "local",
                "cost_tier": "free",
                "context": 4096,
                "timeout": 120,
                "fallbacks": ["local-fast", "local-tiny"],
                "note": "한국어 응답 품질을 우선할 때"
            },
            "local-korean-large": {
                "label": "로컬 한국어 고품질",
                "provider": "local-ollama",
                "model": "exaone3.5:7.8b",
                "capabilities": ["text"],
                "privacy": "local",
                "selectable": False,
                "visible": True,
                "group": "local",
                "cost_tier": "free",
                "context": 8192,
                "timeout": 180,
                "fallbacks": ["local-korean", "local-fast"],
                "note": "RAM 여유가 있을 때 쓰는 고품질 텍스트 모델"
            },
            "local-gemma3-vision": {
                "label": "로컬 고품질 이미지",
                "provider": "local-ollama",
                "model": "gemma3:4b",
                "capabilities": ["text", "image"],
                "privacy": "local",
                "selectable": True,
                "visible": True,
                "group": "vision",
                "cost_tier": "free",
                "context": 8192,
                "timeout": 180,
                "fallbacks": ["local-vision", "local-fast"],
                "note": "이미지를 직접 읽는 비전 백업 후보"
            },
            "local-vision": {
                "label": "로컬 이미지 분석",
                "provider": "local-ollama",
                "model": "moondream",
                "capabilities": ["text", "image"],
                "privacy": "local",
                "selectable": True,
                "visible": True,
                "group": "vision",
                "cost_tier": "free",
                "context": 2048,
                "timeout": 120,
                "fallbacks": ["local-fast"],
                "note": "가벼운 이미지 캡션/설명 백업 후보"
            },
            "local-llava": {
                "label": "로컬 LLaVA",
                "provider": "local-ollama",
                "model": "llava:7b",
                "capabilities": ["text", "image"],
                "privacy": "local",
                "selectable": False,
                "visible": True,
                "group": "vision",
                "cost_tier": "free",
                "context": 4096,
                "timeout": 240,
                "fallbacks": ["local-vision", "local-fast"],
                "note": "성능이 충분할 때 쓰는 비전 모델"
            },
            "api-openrouter-balanced": {
                "label": "API 균형형",
                "provider": "openrouter-main",
                "model": "openai/gpt-4.1-mini",
                "capabilities": ["text", "image", "document"],
                "privacy": "external",
                "selectable": True,
                "visible": True,
                "group": "api",
                "cost_tier": "paid-low",
                "context": 128000,
                "timeout": 180,
                "allow_external_text": True,
                "allow_external_images": True,
                "allow_external_documents": False,
                "fallbacks": ["local-fast"],
                "note": "OpenRouter API 키와 provider enabled 설정 후 사용"
            }
        }
    }

def get_ai_models():
    defaults = get_default_ai_models()
    data = load_json_file(AI_MODELS_FILE, None)
    if not isinstance(data, dict):
        return defaults

    profiles = defaults["profiles"].copy()
    custom_profiles = data.get("profiles", {})
    if isinstance(custom_profiles, dict):
        for name, profile in custom_profiles.items():
            if isinstance(profile, dict):
                merged = profiles.get(name, {}).copy()
                merged.update(profile)
                profiles[name] = merged
    data["profiles"] = profiles
    return data

LEGACY_AI_PROFILE_ALIASES = {
    "qwen2.5:0.5b": "local-tiny",
    "qwen2.5:1.5b": "local-fast",
    "exaone3.5:2.4b": "local-korean",
    "exaone3.5:7.8b": "local-korean-large",
    "moondream": "local-vision",
    "gemma4": "local-gemma4",
    "gemma4:latest": "local-gemma4",
    "gemma3:4b": "local-gemma3-vision",
    "llava:7b": "local-llava"
}

def normalize_ai_profile_id(profile_id):
    clean = str(profile_id or "").strip()
    return LEGACY_AI_PROFILE_ALIASES.get(clean, clean or AI_DEFAULT_MODEL)

def normalize_ai_base_url(base_url, api="ollama"):
    base = (base_url or AI_DEFAULT_BASE_URL).rstrip("/")
    if api in ("openai", "openai_compatible", "openai_responses"):
        return base if base.endswith("/v1") else f"{base}/v1"
    if base.endswith("/v1"):
        return base[:-3]
    return base

def get_ai_model_profile(profile_id, config=None):
    name = normalize_ai_profile_id(profile_id or AI_DEFAULT_MODEL)
    profiles = get_ai_models().get("profiles", {})
    profile = profiles.get(name, {}).copy()
    profile.setdefault("label", name)
    profile.setdefault("provider", AI_DEFAULT_PROVIDER_ID)
    profile.setdefault("capabilities", ["text"])
    profile.setdefault("model", name)
    profile.setdefault("privacy", "local")
    profile.setdefault("selectable", False)
    profile.setdefault("visible", True)
    profile.setdefault("group", "custom")
    profile.setdefault("fallbacks", [])
    profile.setdefault("context", 4096)
    profile.setdefault("timeout", 180)
    profile["name"] = name

    if "api" in profile and "provider" not in profile:
        profile["provider"] = AI_DEFAULT_PROVIDER_ID
    return profile

def get_ai_provider(provider_id):
    provider_id = provider_id or AI_DEFAULT_PROVIDER_ID
    providers = get_ai_providers().get("providers", {})
    provider = providers.get(provider_id, {}).copy()
    provider.setdefault("type", "ollama")
    provider.setdefault("enabled", False)
    provider.setdefault("base_url", AI_DEFAULT_BASE_URL)
    provider.setdefault("privacy", "local")
    provider.setdefault("api_key_env", None)
    provider.setdefault("timeout", 180)
    provider["id"] = provider_id
    return provider

def get_ai_provider_for_profile(profile):
    provider = get_ai_provider(profile.get("provider"))
    if profile.get("api") and profile.get("base_url"):
        provider["type"] = "ollama" if profile["api"] == "ollama" else "openai_compatible"
        provider["base_url"] = profile["base_url"]
        provider["enabled"] = True
    return provider

def get_ai_provider_type(profile):
    return get_ai_provider_for_profile(profile).get("type", "ollama")

def get_ai_provider_display(profile):
    provider = get_ai_provider_for_profile(profile)
    return f"{provider.get('id', profile.get('provider'))} / {provider.get('type')}"

def ai_model_supports(profile, capability):
    return capability in profile.get("capabilities", [])

def get_ai_primary_model(config):
    return config.get("selected_profile") or config.get("primary_model") or config.get("model") or AI_DEFAULT_MODEL

def normalize_ai_profile_list(values):
    if not values:
        return []
    if isinstance(values, str):
        values = [values]
    return [normalize_ai_profile_id(value) for value in values if str(value or "").strip()]

def unique_ai_model_names(*names):
    result = []
    for name in names:
        if not name:
            continue
        clean = str(name).strip()
        if clean and clean not in result:
            result.append(clean)
    return result

def get_ai_settings():
    return load_json_file(AI_SETTINGS_FILE, {"guilds": {}})

def save_ai_settings(data):
    save_json_file(AI_SETTINGS_FILE, data)

def build_default_ai_channel_config(guild=None):
    guild = guild or {}
    selected_profile = normalize_ai_profile_id(
        guild.get("selected_profile") or guild.get("primary_model") or guild.get("model", AI_DEFAULT_MODEL)
    )
    fallback_profiles = normalize_ai_profile_list(
        guild.get("fallback_profiles") or guild.get("fallback_text_model") or AI_DEFAULT_FALLBACK_TEXT_MODEL
    )
    raw_vision_profile = guild.get("vision_profile", guild.get("fallback_vision_model", AI_DEFAULT_FALLBACK_VISION_MODEL))
    vision_profile = "" if raw_vision_profile == "" else normalize_ai_profile_id(raw_vision_profile)
    document_profile = normalize_ai_profile_id(guild.get("document_profile") or AI_DEFAULT_DOCUMENT_MODEL)
    return {
        "enabled": False,
        "mode": "mention",
        "selected_profile": selected_profile,
        "primary_model": selected_profile,
        "model": selected_profile,
        "fallback_profiles": fallback_profiles,
        "fallback_text_model": fallback_profiles[0] if fallback_profiles else AI_DEFAULT_FALLBACK_TEXT_MODEL,
        "vision_profile": vision_profile,
        "fallback_vision_model": vision_profile,
        "document_profile": document_profile,
        "route_policy": guild.get("route_policy", "selected_first"),
        "fallback_policy": guild.get("fallback_policy", AI_DEFAULT_FALLBACK_POLICY),
        "temperature": guild.get("temperature", 0.7),
        "max_tokens": guild.get("max_tokens", AI_DEFAULT_MAX_TOKENS),
        "reply_mode": guild.get("reply_mode", "auto"),
        "reply_inline_limit": clamp_discord_inline_limit(guild.get("reply_inline_limit", AI_REPLY_INLINE_LIMIT))
    }

def normalize_ai_channel_config(config):
    config = config.copy()
    selected_profile = normalize_ai_profile_id(
        config.get("selected_profile") or config.get("primary_model") or config.get("model") or AI_DEFAULT_MODEL
    )
    fallback_profiles = normalize_ai_profile_list(
        config.get("fallback_profiles") or config.get("fallback_text_model") or AI_DEFAULT_FALLBACK_TEXT_MODEL
    )
    raw_vision_profile = config.get("vision_profile", config.get("fallback_vision_model", AI_DEFAULT_FALLBACK_VISION_MODEL))
    vision_profile = "" if raw_vision_profile == "" else normalize_ai_profile_id(raw_vision_profile)
    document_profile = normalize_ai_profile_id(config.get("document_profile") or AI_DEFAULT_DOCUMENT_MODEL)

    config["selected_profile"] = selected_profile
    config["primary_model"] = selected_profile
    config["model"] = selected_profile
    config["fallback_profiles"] = fallback_profiles
    config["fallback_text_model"] = fallback_profiles[0] if fallback_profiles else ""
    config["vision_profile"] = vision_profile
    config["fallback_vision_model"] = vision_profile
    config["document_profile"] = document_profile
    config.setdefault("route_policy", "selected_first")
    config.setdefault("fallback_policy", AI_DEFAULT_FALLBACK_POLICY)
    config.setdefault("temperature", 0.7)
    config.setdefault("max_tokens", AI_DEFAULT_MAX_TOKENS)
    if config.get("reply_mode") not in ("auto", "file", "split"):
        config["reply_mode"] = "auto"
    else:
        config.setdefault("reply_mode", "auto")
    config["reply_inline_limit"] = clamp_discord_inline_limit(config.get("reply_inline_limit", AI_REPLY_INLINE_LIMIT))
    return config

def get_ai_channel_config(guild_id, channel_id, create=False):
    data = get_ai_settings()
    guilds = data.setdefault("guilds", {})
    guild = guilds.setdefault(str(guild_id), {"channels": {}})
    channels = guild.setdefault("channels", {})
    default_config = build_default_ai_channel_config(guild)

    channel_key = str(channel_id)
    if channel_key not in channels:
        if not create:
            return default_config
        channels[channel_key] = default_config.copy()
        save_ai_settings(data)

    config = default_config.copy()
    config.update(channels[channel_key])
    return normalize_ai_channel_config(config)

def set_ai_channel_config(guild_id, channel_id, **updates):
    data = get_ai_settings()
    guild = data.setdefault("guilds", {}).setdefault(str(guild_id), {"channels": {}})
    channels = guild.setdefault("channels", {})
    config = channels.setdefault(str(channel_id), build_default_ai_channel_config(guild))
    if "selected_profile" in updates:
        updates["selected_profile"] = normalize_ai_profile_id(updates["selected_profile"])
        updates.setdefault("primary_model", updates["selected_profile"])
        updates.setdefault("model", updates["selected_profile"])
    elif "primary_model" in updates:
        updates["selected_profile"] = normalize_ai_profile_id(updates["primary_model"])
        updates["primary_model"] = updates["selected_profile"]
        updates.setdefault("model", updates["selected_profile"])
    elif "model" in updates:
        updates["selected_profile"] = normalize_ai_profile_id(updates["model"])
        updates["model"] = updates["selected_profile"]
        updates.setdefault("primary_model", updates["selected_profile"])

    if "fallback_profiles" in updates:
        updates["fallback_profiles"] = normalize_ai_profile_list(updates["fallback_profiles"])
        updates["fallback_text_model"] = updates["fallback_profiles"][0] if updates["fallback_profiles"] else ""
    elif "fallback_text_model" in updates:
        updates["fallback_profiles"] = normalize_ai_profile_list(updates["fallback_text_model"])
        updates["fallback_text_model"] = updates["fallback_profiles"][0] if updates["fallback_profiles"] else ""

    if "vision_profile" in updates:
        updates["vision_profile"] = "" if updates["vision_profile"] == "" else normalize_ai_profile_id(updates["vision_profile"])
        updates["fallback_vision_model"] = updates["vision_profile"]
    elif "fallback_vision_model" in updates:
        updates["vision_profile"] = "" if updates["fallback_vision_model"] == "" else normalize_ai_profile_id(updates["fallback_vision_model"])
        updates["fallback_vision_model"] = updates["vision_profile"]

    if "document_profile" in updates:
        updates["document_profile"] = normalize_ai_profile_id(updates["document_profile"])

    config.update(updates)
    channels[str(channel_id)] = normalize_ai_channel_config(config)
    save_ai_settings(data)
    return channels[str(channel_id)]

def get_memory_bucket(memory, guild_id, channel_id):
    guild = memory.setdefault(str(guild_id), {})
    return guild.setdefault(str(channel_id), [])

def append_ai_memory(file_path, guild_id, channel_id, role, content, author=None, attachments=None, trim=None):
    memory = load_json_file(file_path, {})
    bucket = get_memory_bucket(memory, guild_id, channel_id)
    entry = {
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "role": role,
        "content": content
    }
    if author:
        entry["author"] = author
    if attachments:
        entry["attachments"] = attachments
    bucket.append(entry)
    if trim and len(bucket) > trim:
        del bucket[:-trim]
    save_json_file(file_path, memory)

def get_ai_short_memory(guild_id, channel_id):
    memory = load_json_file(AI_SHORT_MEMORY_FILE, {})
    return memory.get(str(guild_id), {}).get(str(channel_id), [])[-AI_SHORT_MEMORY_LIMIT:]

def count_ai_memory(file_path, guild_id, channel_id):
    memory = load_json_file(file_path, {})
    return len(memory.get(str(guild_id), {}).get(str(channel_id), []))

def strip_bot_mention(content):
    if not bot.user:
        return content.strip()
    return re.sub(rf"<@!?{bot.user.id}>", "", content).strip()

def is_ai_triggered(message, config):
    if not config.get("enabled"):
        return False
    if message.content.startswith("!"):
        return False
    if config.get("mode") == "always":
        return bool(message.content.strip() or message.attachments)
    return bot.user in message.mentions

def summarize_attachments_for_memory(attachments):
    if not attachments:
        return []
    return [
        {
            "filename": attachment.filename,
            "size": attachment.size,
            "content_type": attachment.content_type
        }
        for attachment in attachments
    ]

def decode_text_bytes(data):
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")

def truncate_for_prompt(text, limit=6000):
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "\n...[내용이 길어 일부만 사용됨]"

def clamp_discord_inline_limit(value, default=AI_REPLY_INLINE_LIMIT):
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = int(default)
    return max(500, min(DISCORD_SAFE_MESSAGE_LIMIT, limit))

def extract_docx_text(data):
    with zipfile.ZipFile(io.BytesIO(data)) as docx:
        xml_data = docx.read("word/document.xml")
    root = ET.fromstring(xml_data)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    texts = [node.text for node in root.findall(".//w:t", namespace) if node.text]
    return "\n".join(texts)

def extract_pdf_text(data):
    reader_cls = None
    try:
        from pypdf import PdfReader
        reader_cls = PdfReader
    except Exception:
        try:
            from PyPDF2 import PdfReader
            reader_cls = PdfReader
        except Exception:
            return "PDF 텍스트 추출 라이브러리(pypdf 또는 PyPDF2)가 없어 본문을 읽지 못했습니다."

    reader = reader_cls(io.BytesIO(data))
    pages = []
    for index, page in enumerate(reader.pages):
        if index >= 8:
            break
        pages.append(page.extract_text() or "")
    return "\n".join(pages).strip() or "PDF에서 추출 가능한 텍스트를 찾지 못했습니다."

def try_ocr_image(data, filename):
    info = [f"이미지 파일명: {filename}"]
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(data))
        info.append(f"이미지 크기: {image.width}x{image.height}, 형식: {image.format}")
    except Exception:
        image = None

    if image is not None:
        try:
            import pytesseract
            text = pytesseract.image_to_string(image, lang="kor+eng").strip()
            if text:
                info.append("OCR 텍스트:\n" + truncate_for_prompt(text, 2500))
        except Exception:
            info.append("OCR 도구가 없어 이미지 텍스트는 추출하지 못했습니다.")

    return "\n".join(info)

async def read_ai_attachment(attachment):
    if attachment.size > AI_MAX_ATTACHMENT_BYTES:
        return None, f"{attachment.filename}: 파일이 너무 큽니다. 최대 {AI_MAX_ATTACHMENT_BYTES // (1024 * 1024)}MB까지 처리합니다."
    try:
        return await attachment.read(), None
    except Exception as e:
        return None, f"{attachment.filename}: 다운로드 실패 ({e})"

async def process_ai_attachments(attachments):
    text_blocks = []
    image_payloads = []
    image_fallbacks = []
    notes = []

    for attachment in attachments:
        filename = attachment.filename or "attachment"
        ext = os.path.splitext(filename)[1].lower()
        data, error = await read_ai_attachment(attachment)
        if error:
            notes.append(error)
            continue

        if ext in AI_ALLOWED_IMAGE_EXTENSIONS or (attachment.content_type or "").startswith("image/"):
            mime = attachment.content_type or "image/png"
            encoded = base64.b64encode(data).decode("ascii")
            image_payloads.append({
                "filename": filename,
                "mime": mime,
                "base64": encoded
            })
            image_fallbacks.append(try_ocr_image(data, filename))
            notes.append(f"{filename}: 이미지 첨부를 직접 분석 가능한 형식으로 준비했습니다.")
        elif ext in AI_ALLOWED_TEXT_EXTENSIONS:
            text = truncate_for_prompt(decode_text_bytes(data))
            text_blocks.append(f"[첨부 문서: {filename}]\n{text}")
        elif ext == ".docx":
            try:
                text_blocks.append(f"[DOCX 문서: {filename}]\n{truncate_for_prompt(extract_docx_text(data))}")
            except Exception as e:
                notes.append(f"{filename}: DOCX 추출 실패 ({e})")
        elif ext == ".pdf":
            text_blocks.append(f"[PDF 문서: {filename}]\n{truncate_for_prompt(extract_pdf_text(data))}")
        else:
            notes.append(f"{filename}: 지원하지 않는 첨부 형식입니다.")

    return text_blocks, image_payloads, image_fallbacks, notes

class AiModelUnsupportedError(RuntimeError):
    pass

def classify_ai_error(error):
    text = str(error).lower()
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "connect" in text or "connection" in text or "cannot connect" in text:
        return "connection"
    if "context" in text or "num_ctx" in text or "maximum context" in text:
        return "context"
    if "image" in text or "vision" in text or "multimodal" in text:
        return "unsupported_image"
    return "server"

def build_openai_image_parts(image_payloads):
    parts = []
    for payload in image_payloads or []:
        mime = payload.get("mime") or "image/png"
        encoded = payload.get("base64")
        if encoded:
            parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{encoded}"}
            })
    return parts

def get_ai_request_timeout(profile, config):
    provider = get_ai_provider_for_profile(profile)
    return int(profile.get("timeout") or provider.get("timeout") or config.get("timeout") or 180)

def get_ai_max_tokens(profile, config):
    profile_tokens = int(profile.get("max_tokens") or 0)
    config_tokens = int(config.get("max_tokens") or 0)
    if config_tokens and config_tokens not in (800, AI_DEFAULT_MAX_TOKENS):
        return config_tokens
    if profile_tokens:
        return profile_tokens
    if config_tokens:
        return max(config_tokens, AI_DEFAULT_MAX_TOKENS)
    return AI_DEFAULT_MAX_TOKENS

def get_provider_headers(provider):
    headers = {}
    api_key_env = provider.get("api_key_env")
    if api_key_env:
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise RuntimeError(f"{provider.get('id')} provider의 환경 변수 `{api_key_env}`가 없습니다.")
        headers["Authorization"] = f"Bearer {api_key}"
    return headers

def ensure_provider_available(profile):
    provider = get_ai_provider_for_profile(profile)
    if not provider.get("enabled", False):
        raise RuntimeError(f"{provider.get('id')} provider가 서버 설정에서 비활성화되어 있습니다.")
    if provider.get("api_key_env") and not os.getenv(provider["api_key_env"]):
        raise RuntimeError(f"{provider.get('id')} provider의 API 키 환경 변수 `{provider['api_key_env']}`가 없습니다.")
    return provider

def profile_allows_external(profile, task):
    provider = get_ai_provider_for_profile(profile)
    if provider.get("privacy") != "external" and profile.get("privacy") != "external":
        return True
    if task == "image":
        return bool(profile.get("allow_external_images", False))
    if task == "document":
        return bool(profile.get("allow_external_documents", False))
    return bool(profile.get("allow_external_text", True))

def append_ai_usage_log(message, profile, task, success, duration_ms, error=None):
    provider = get_ai_provider_for_profile(profile)
    entry = {
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "guild_id": str(message.guild.id) if message.guild else None,
        "channel_id": str(message.channel.id) if message.channel else None,
        "profile": profile.get("name"),
        "provider": provider.get("id"),
        "provider_type": provider.get("type"),
        "model": profile.get("model"),
        "task": task,
        "success": success,
        "duration_ms": int(duration_ms)
    }
    if error:
        entry["error"] = truncate_text(error, 300)
    try:
        with open(AI_USAGE_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as log_error:
        print(f"AI 사용량 로그 저장 실패: {log_error}")

async def call_openai_compatible_chat(config, provider, profile, message, prompt_text, image_payloads, memory_content, use_images=False):
    base_url = normalize_ai_base_url(provider.get("base_url"), "openai_compatible")
    messages = build_ai_messages(
        message,
        prompt_text,
        image_payloads if use_images else [],
        memory_content,
        include_openai_images=use_images
    )
    payload = {
        "model": profile.get("model", profile["name"]),
        "messages": messages,
        "temperature": float(config.get("temperature", 0.7)),
        "max_tokens": get_ai_max_tokens(profile, config),
        "stream": False
    }
    timeout = aiohttp.ClientTimeout(total=get_ai_request_timeout(profile, config))
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(f"{base_url}/chat/completions", json=payload, headers=get_provider_headers(provider)) as response:
            body = await response.text()
            if response.status >= 400:
                raise RuntimeError(f"LLM 서버 오류 {response.status}: {body[:500]}")
            data = json.loads(body)
    return data["choices"][0]["message"]["content"].strip()

async def call_ollama_native_chat(config, provider, profile, message, prompt_text, image_payloads, memory_content, use_images=False):
    base_url = normalize_ai_base_url(provider.get("base_url"), "ollama")
    messages = build_ai_messages(message, prompt_text, [], memory_content)
    if use_images:
        images = [payload["base64"] for payload in image_payloads or [] if payload.get("base64")]
        if images:
            messages[-1]["images"] = images

    options = {
        "temperature": float(config.get("temperature", 0.7)),
        "num_predict": get_ai_max_tokens(profile, config)
    }
    if profile.get("context"):
        options["num_ctx"] = int(profile["context"])

    payload = {
        "model": profile.get("model", profile["name"]),
        "messages": messages,
        "options": options,
        "stream": False
    }
    timeout = aiohttp.ClientTimeout(total=get_ai_request_timeout(profile, config))
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(f"{base_url}/api/chat", json=payload) as response:
            body = await response.text()
            if response.status >= 400:
                raise RuntimeError(f"Ollama 서버 오류 {response.status}: {body[:500]}")
            data = json.loads(body)

    answer = data.get("message", {}).get("content", "")
    if not answer:
        raise RuntimeError("Ollama 응답에 message.content가 없습니다.")
    return answer.strip()

async def call_ai_model(config, profile, message, prompt_text, image_payloads, memory_content, use_images=False):
    if use_images and not ai_model_supports(profile, "image"):
        raise AiModelUnsupportedError(f"{profile['name']} 모델은 이미지 입력을 지원하지 않습니다.")

    provider = ensure_provider_available(profile)
    provider_type = provider.get("type", "ollama")
    if provider_type == "openai_compatible":
        return await call_openai_compatible_chat(
            config, provider, profile, message, prompt_text, image_payloads, memory_content, use_images
        )
    if provider_type == "ollama":
        return await call_ollama_native_chat(
            config, provider, profile, message, prompt_text, image_payloads, memory_content, use_images
        )
    raise RuntimeError(f"지원하지 않는 AI provider 형식입니다: {provider_type}")

def build_ai_messages(message, prompt_text, image_payloads=None, current_memory_content=None, include_openai_images=False):
    history = get_ai_short_memory(message.guild.id, message.channel.id)
    if current_memory_content and history and history[-1].get("content") == current_memory_content:
        history = history[:-1]
    messages = [{
        "role": "system",
        "content": AI_SYSTEM_PROMPT
    }]

    for item in history[-AI_SHORT_MEMORY_LIMIT:]:
        role = item.get("role")
        if role in ("user", "assistant") and item.get("content"):
            messages.append({"role": role, "content": truncate_for_prompt(item["content"], 2000)})

    image_parts = build_openai_image_parts(image_payloads) if include_openai_images else []
    if image_parts:
        content = [{"type": "text", "text": prompt_text}]
        content.extend(image_parts)
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": prompt_text})
    return messages

def split_discord_message(text, limit=DISCORD_SAFE_MESSAGE_LIMIT):
    chunks = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < 500:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks

def split_text_by_utf8_bytes(text, byte_limit):
    chunks = []
    current = []
    current_size = 0
    for char in text:
        char_size = len(char.encode("utf-8"))
        if current and current_size + char_size > byte_limit:
            chunks.append("".join(current))
            current = [char]
            current_size = char_size
        else:
            current.append(char)
            current_size += char_size
    if current:
        chunks.append("".join(current))
    return chunks or [""]

def build_ai_answer_file_text(message, answer, route=None):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    guild_name = message.guild.name if message.guild else "DM"
    channel_name = getattr(message.channel, "name", str(message.channel))
    author_name = getattr(message.author, "display_name", str(message.author))
    metadata = [
        "PuangBOT AI Response",
        f"Time: {now}",
        f"Guild: {guild_name}",
        f"Channel: {channel_name}",
        f"User: {author_name}"
    ]
    if route:
        metadata.append(f"Route: {route}")
    return "\n".join(metadata) + "\n\n--- Answer ---\n\n" + (answer or "")

def build_ai_answer_filename(index=0, total=1):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_part{index + 1:02d}" if total > 1 else ""
    return f"puangbot_ai_{timestamp}{suffix}.txt"

async def send_ai_answer(message, answer, route=None, config=None):
    answer = (answer or "").strip() or "(빈 응답)"
    config = config or {}
    reply_mode = config.get("reply_mode", "auto")
    if reply_mode not in ("auto", "file", "split"):
        reply_mode = "auto"
    inline_limit = clamp_discord_inline_limit(config.get("reply_inline_limit", AI_REPLY_INLINE_LIMIT))

    if reply_mode == "split":
        for index, chunk in enumerate(split_discord_message(answer)):
            if index == 0:
                await message.reply(chunk, mention_author=False)
            else:
                await message.channel.send(chunk)
        return

    if reply_mode == "auto" and len(answer) <= inline_limit:
        await message.reply(answer, mention_author=False)
        return

    intro_prefix = "답변이 길어서 전체 내용은 텍스트 파일로 첨부했어요.\n\n미리보기:\n"
    preview_limit = min(AI_REPLY_PREVIEW_LIMIT, max(100, DISCORD_SAFE_MESSAGE_LIMIT - len(intro_prefix) - 40))
    preview = truncate_for_prompt(answer, preview_limit)
    file_text = build_ai_answer_file_text(message, answer, route)
    file_chunks = split_text_by_utf8_bytes(file_text, AI_REPLY_FILE_BYTE_LIMIT)
    total = len(file_chunks)
    intro = intro_prefix + preview
    if len(intro) > DISCORD_SAFE_MESSAGE_LIMIT:
        intro = intro[:DISCORD_SAFE_MESSAGE_LIMIT - 20].rstrip() + "\n..."

    try:
        for index, chunk in enumerate(file_chunks):
            file_data = io.BytesIO(chunk.encode("utf-8"))
            file = discord.File(file_data, filename=build_ai_answer_filename(index, total))
            if index == 0:
                await message.reply(intro, file=file, mention_author=False)
            else:
                await message.channel.send(f"긴 답변 이어서 첨부합니다. ({index + 1}/{total})", file=file)
    except Exception:
        for index, chunk in enumerate(split_discord_message(answer)):
            if index == 0:
                await message.reply(chunk, mention_author=False)
            else:
                await message.channel.send(chunk)

def clamp_percent(value, minimum=0, maximum=200):
    return max(minimum, min(maximum, int(value)))

def scale_pcm(data, volume):
    if not data:
        return data
    if volume <= 0:
        return b"\x00" * len(data)
    if abs(volume - 1.0) < 0.001:
        return data

    samples = array("h")
    samples.frombytes(data)
    if sys.byteorder != "little":
        samples.byteswap()

    for i, sample in enumerate(samples):
        adjusted = int(sample * volume)
        if adjusted > 32767:
            adjusted = 32767
        elif adjusted < -32768:
            adjusted = -32768
        samples[i] = adjusted

    if sys.byteorder != "little":
        samples.byteswap()
    return samples.tobytes()

def mix_pcm(left, right):
    if not left:
        return right
    if not right:
        return left

    frame_len = max(len(left), len(right))
    if len(left) < frame_len:
        left += b"\x00" * (frame_len - len(left))
    if len(right) < frame_len:
        right += b"\x00" * (frame_len - len(right))

    left_samples = array("h")
    right_samples = array("h")
    left_samples.frombytes(left)
    right_samples.frombytes(right)

    if sys.byteorder != "little":
        left_samples.byteswap()
        right_samples.byteswap()

    for i, sample in enumerate(right_samples):
        mixed = left_samples[i] + sample
        if mixed > 32767:
            mixed = 32767
        elif mixed < -32768:
            mixed = -32768
        left_samples[i] = mixed

    if sys.byteorder != "little":
        left_samples.byteswap()
    return left_samples.tobytes()
# -----------------------------------

# ==========================================
# 🌟 [신규] FFmpeg 자동 다운로드 시스템
# ==========================================
def check_and_setup_env():
    print("🔄 [시스템 점검] 봇 구동 환경을 확인합니다...")

    sys_name = platform.system()
    ffmpeg_name = "ffmpeg.exe" if sys_name == "Windows" else "ffmpeg"

    # 1. 이미 다운받았는지 확인
    if os.path.exists(ffmpeg_name) or shutil.which("ffmpeg"):
        print("✅ FFmpeg가 이미 준비되어 있습니다.")
        return

    # 2. 없다면 자동으로 깃허브에서 다운로드하여 압축 풀기
    print(f"📥 FFmpeg가 없습니다! 깡통 서버를 위해 자동으로 다운로드합니다 (OS: {sys_name})...")
    try:
        if sys_name == "Windows":
            url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            zip_path = "ffmpeg_temp.zip"
            urllib.request.urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file in zip_ref.namelist():
                    if file.endswith("ffmpeg.exe"):
                        with zip_ref.open(file) as source, open(ffmpeg_name, "wb") as target:
                            target.write(source.read())
            os.remove(zip_path)
            print("🎉 FFmpeg 자동 설치 완료!")
    except Exception as e:
        print(f"❌ FFmpeg 다운로드 실패: {e}")

# 봇이 켜질 때 무조건 환경 세팅 먼저 실행
check_and_setup_env()

# 다운받은 FFmpeg의 절대 경로 저장 (재생 오류 원천 차단)
FFMPEG_PATH = os.path.abspath("ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg")
# ==========================================


# [설정] 봇 기본 설정
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

OWNER_ID = 495511094434201600  # ⚠️ 오너 ID 유지됨

# [설정] server.properties에 적었던 비밀번호
RCON_PASSWORD = "puang6974"

# 🌟 경험치 데이터 저장용 파일 이름
XP_FILE = "puang_xp.json"

# ==========================================
# 🛠️ 서버 관리 경로 설정 (상대 경로 기준 - 수정됨)
# ==========================================
# 봇 위치: Desktop\ET\PuangBOT\puang.py
# .. 를 통해 Desktop\ET 폴더로 이동합니다.
BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 🌟 중요: 스크린샷에 맞춰 'serve'를 'server'로 수정했습니다!
MC_ROOT_DIR = os.path.join(BASE_PATH, "server", "mc")  # Desktop\ET\server\mc
PLAYIT_DIR = os.path.join(BASE_PATH, "server")        # Desktop\ET\server
PLAYIT_LINK = "playit.gg.lnk"                         # 바로가기 파일명

# [디버깅용] 봇이 켜질 때 실제 경로를 콘솔에 출력해서 확인하게 합니다.
print(f"📂 [경로 확인] 마크 루트: {MC_ROOT_DIR}")
print(f"📂 [경로 확인] Playit 폴더: {PLAYIT_DIR}")

FFMPEG_FILTERS = {
    'normal': '',
    'bassboost': 'bass=g=20,dynaudnorm=f=200',
    'nightcore': 'asetrate=44100*1.25,aresample=44100,atempo=1.0',
    'slowed': 'asetrate=44100*0.8,aresample=44100,atempo=1.0',
    '8d': 'apulsator=hz=0.08',
    'vaporwave': 'aresample=48000,asetrate=48000*0.8'
}

def can_manage_music_settings(member):
    return (
        member.id == OWNER_ID
        or member.guild_permissions.manage_guild
        or any(role.name.upper() == "DJ" for role in member.roles)
    )

def can_manage_ai_settings(member):
    return member.id == OWNER_ID or member.guild_permissions.manage_guild

class Song:
    def __init__(self, url, title, duration, thumbnail, requester):
        self.url = url
        self.title = title
        self.duration = duration
        self.thumbnail = thumbnail
        self.requester = requester

class GuildState:
    def __init__(self):
        self.queue = []          
        self.is_playing = False
        self.volume = 0.5        
        self.tts_duck_volume = 0.5
        self.tts_volume = 1.2
        self.loop_mode = 0       
        self.current_song = None
        self.voice_client = None
        self.music_source = None
        self.mixer = None
        self.filter = 'normal'   
        self.start_time = 0      
        self.controller_msg = None 
        self.playback_channel = None
        self.queue_page = 0
        self.skip_votes = set() 
        # --- [수정: TTS 큐 시스템 추가] ---
        self.tts_queue = asyncio.Queue()
        self.tts_sources = Queue()
        self.tts_task = None
        # --- [추가: 마지막으로 TTS를 사용한 유저 기억] ---
        self.last_tts_user = None
        # -----------------------------------

guild_states = {}

class MixedAudioSource(discord.AudioSource):
    def __init__(self, state):
        self.state = state
        self.active_tts = None
        self.closed = False
        self.music_multiplier = 1.0

    def is_opus(self):
        return False

    def read(self):
        if self.closed:
            return b""

        music_data = self._read_music_frame()
        tts_data = self._read_tts_frame()
        tts_active = bool(tts_data) or self.active_tts is not None or not self.state.tts_sources.empty()

        if music_data:
            target = self.state.tts_duck_volume if tts_active else 1.0
            music_data = scale_pcm(music_data, self._smooth_music_multiplier(target))

        if music_data and tts_data:
            return mix_pcm(music_data, tts_data)
        if tts_data:
            return tts_data
        if music_data:
            return music_data
        return b""

    def cleanup(self):
        self.closed = True
        self._cleanup_music()
        self._cleanup_active_tts()
        while True:
            try:
                item = self.state.tts_sources.get_nowait()
            except Empty:
                break
            self._cleanup_tts_item(item)

    def _smooth_music_multiplier(self, target):
        step = 0.08
        if abs(self.music_multiplier - target) <= step:
            self.music_multiplier = target
        elif self.music_multiplier < target:
            self.music_multiplier += step
        else:
            self.music_multiplier -= step
        return self.music_multiplier

    def _read_music_frame(self):
        source = self.state.music_source
        if source is None:
            return b""

        data = source.read()
        if data:
            return data

        self._cleanup_music()
        return b""

    def _read_tts_frame(self):
        while True:
            if self.active_tts is None:
                try:
                    self.active_tts = self.state.tts_sources.get_nowait()
                except Empty:
                    return b""

            data = self.active_tts["source"].read()
            if data:
                return data

            self._cleanup_active_tts()

    def _cleanup_music(self):
        if self.state.music_source is None:
            return
        try:
            self.state.music_source.cleanup()
        except Exception:
            pass
        self.state.music_source = None

    def _cleanup_active_tts(self):
        if self.active_tts is None:
            return
        self._cleanup_tts_item(self.active_tts)
        self.active_tts = None

    def _cleanup_tts_item(self, item):
        try:
            item["source"].cleanup()
        except Exception:
            pass
        try:
            os.remove(item["filename"])
        except Exception:
            pass

def start_mixer_if_needed(guild_id, interaction_channel=None):
    state = get_state(guild_id)
    voice = state.voice_client
    if not voice or not voice.is_connected():
        return False

    if interaction_channel is not None:
        state.playback_channel = interaction_channel

    if voice.is_playing() or voice.is_paused():
        return True

    state.mixer = MixedAudioSource(state)

    def after_mixer(error):
        if error:
            print(f"믹서 오류: {error}")
        state.mixer = None

        if state.current_song or state.queue:
            channel = interaction_channel or state.playback_channel
            coro = play_next(guild_id, channel)
            fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"다음 곡 재생 오류: {e}")

    voice.play(state.mixer, after=after_mixer)
    return True

def load_xp():
    try:
        with open(XP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_xp(data):
    with open(XP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_required_xp(level):
    # 레벨이 오를수록 기하급수적으로 증가하는 요구 경험치 곡선
    return int(100 * (level ** 1.5))

async def add_xp(user: discord.Member, amount: int, channel: discord.TextChannel = None):
    if user.bot: return

    data = load_xp()
    uid = str(user.id)

    # 신규 유저 초기화
    if uid not in data:
        data[uid] = {"xp": 0, "level": 1}

    data[uid]["xp"] += amount
    current_level = data[uid]["level"]
    required_xp = get_required_xp(current_level)

    # 레벨업 판정
    if data[uid]["xp"] >= required_xp:
        data[uid]["level"] += 1
        data[uid]["xp"] -= required_xp  # 초과 경험치 이월
        new_level = data[uid]["level"]
        save_xp(data)

        # 레벨업 축하 메시지 출력
        if channel:
            await channel.send(f"🎉 빰빠밤! {user.mention}님이 **레벨 {new_level}**(으)로 올랐습니다! 푸앙푸앙!")
            
        # 💡 [역할 부여 로직] 디스코드 서버에 'Lv.10', 'Lv.20' 같은 역할이 미리 만들어져 있어야 합니다.
        # role_name = f"Lv.{new_level}"
        # role = discord.utils.get(user.guild.roles, name=role_name)
        # if role:
        #     try: await user.add_roles(role)
        #     except: pass
    else:
        save_xp(data)

# --- [수정: TTS 처리 백그라운드 엔진 (gTTS & Edge-TTS 하이브리드)] ---
async def process_tts_queue(guild: discord.Guild):
    state = get_state(guild.id)
    vc = guild.voice_client
    
    while not state.tts_queue.empty():
        payload = await state.tts_queue.get()
        
        if not vc or not vc.is_connected():
            break

        try:
            filename = f"tts_{uuid.uuid4().hex}.mp3"
            
            # 1. 유저 설정에 따라 엔진 분기 처리
            if payload.get("engine") == "edge":
                communicate = edge_tts.Communicate(payload["text"], payload["voice"], pitch=payload["pitch"])
                await communicate.save(filename)
            else:
                # 기본 엔진 (gTTS)
                tts = gTTS(text=payload["text"], lang='ko')
                tts.save(filename)
            
            # 2. 믹서에 TTS 소스를 추가합니다. 음악은 끊기지 않고 자동으로 볼륨만 낮아집니다.
            tts_source = discord.FFmpegPCMAudio(filename, executable=FFMPEG_PATH)
            tts_source = discord.PCMVolumeTransformer(tts_source, volume=state.tts_volume)
            state.tts_sources.put({"source": tts_source, "filename": filename})
            filename = None

            if not start_mixer_if_needed(guild.id):
                item = state.tts_sources.get_nowait()
                try:
                    item["source"].cleanup()
                except Exception:
                    pass
                try:
                    os.remove(item["filename"])
                except Exception:
                    pass

        except Exception as e:
            print(f"TTS 에러: {e}")
            if filename:
                try: os.remove(filename)
                except: pass
# -----------------------------------

def get_state(guild_id):
    if guild_id not in guild_states:
        state = GuildState()
        saved = load_volume_settings().get(str(guild_id), {})
        state.volume = float(saved.get("music_volume", state.volume))
        state.tts_duck_volume = float(saved.get("tts_duck_volume", state.tts_duck_volume))
        guild_states[guild_id] = state
    return guild_states[guild_id]

def format_time(seconds):
    return str(datetime.timedelta(seconds=int(seconds))) if seconds else "실시간"

QUEUE_PAGE_SIZE = 10
LOOP_MODE_NAMES = ["끔", "한 곡", "전체"]
UI_COLORS = {
    "info": discord.Color.blurple(),
    "success": discord.Color.green(),
    "warning": discord.Color.orange(),
    "error": discord.Color.red(),
    "music": discord.Color.from_rgb(255, 105, 180),
    "ai": discord.Color.from_rgb(88, 166, 255),
    "server": discord.Color.from_rgb(96, 205, 118),
    "tts": discord.Color.from_rgb(186, 140, 255),
    "neutral": discord.Color.dark_gray()
}

def truncate_text(text, limit=80):
    text = str(text or "")
    return text if len(text) <= limit else text[:limit - 3] + "..."

def build_embed(title=None, description=None, kind="info", color=None):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color or UI_COLORS.get(kind, UI_COLORS["info"]),
        timestamp=datetime.datetime.now()
    )
    embed.set_footer(text="PuangBOT")
    return embed

def build_status_embed(title, description=None, kind="info"):
    return build_embed(title=title, description=description, kind=kind)

def progress_bar(current, total, size=16):
    if not total or total <= 0:
        return "▰" + "▱" * (size - 1)
    ratio = max(0, min(1, current / total))
    filled = max(1, int(ratio * size)) if current > 0 else 0
    return "▰" * filled + "▱" * (size - filled)

async def send_status(interaction, title, description=None, kind="info", ephemeral=True):
    embed = build_status_embed(title, description, kind)
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

class ConfirmView(discord.ui.View):
    def __init__(self, owner_id, on_confirm, title="확인", danger=True, timeout=30):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.on_confirm = on_confirm
        self.title = title
        for child in self.children:
            if getattr(child, "label", "") == "확인":
                child.style = discord.ButtonStyle.danger if danger else discord.ButtonStyle.success

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await send_status(interaction, "권한 없음", "이 확인 창을 연 사용자만 조작할 수 있습니다.", "error", True)
            return False
        return True

    @discord.ui.button(label="확인", emoji="✅", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await self.on_confirm(interaction)

    @discord.ui.button(label="취소", emoji="✖️", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            embed=build_status_embed(f"{self.title} 취소됨", "요청을 실행하지 않았습니다.", "neutral"),
            view=self
        )

def requester_label(song):
    requester = getattr(song, "requester", None)
    if requester is None:
        return "알 수 없음"
    return getattr(requester, "display_name", str(requester))

def get_playback_status(state):
    vc = state.voice_client
    if vc and vc.is_paused():
        return "일시정지"
    if state.current_song:
        return "재생 중"
    return "대기 중"

def get_skip_vote_text(state):
    vc = state.voice_client
    current_song = state.current_song
    if not vc or not current_song or not getattr(vc, "channel", None):
        return "0 / 0"

    members = [m for m in vc.channel.members if not m.bot]
    required_votes = max(1, (len(members) + 1) // 2)
    return f"{len(state.skip_votes)} / {required_votes}"

def build_now_playing_embed(state):
    song = state.current_song
    embed = build_embed(kind="music")

    if not song:
        embed.title = "🎵 음악 대기 중"
        embed.description = "대기열에 노래를 추가하면 이 패널이 자동으로 갱신됩니다."
        embed.add_field(name="대기열", value=f"{len(state.queue)}곡", inline=True)
        embed.add_field(name="반복", value=LOOP_MODE_NAMES[state.loop_mode], inline=True)
        embed.add_field(name="볼륨", value=f"음악 {int(state.volume * 100)}% · TTS 중 {int(state.tts_duck_volume * 100)}%", inline=True)
        return embed

    elapsed = max(0, int(time.time() - state.start_time))
    if song.duration:
        elapsed = min(elapsed, int(song.duration))
        time_text = f"`{format_time(elapsed)} / {format_time(song.duration)}`"
        bar_text = progress_bar(elapsed, int(song.duration))
    else:
        time_text = "`실시간`"
        bar_text = "▰" + "▱" * 15

    next_song = state.queue[0].title if state.queue else "없음"
    embed.title = "🎧 지금 재생 중"
    embed.description = f"**[{truncate_text(song.title, 180)}]({song.url})**\n{bar_text}\n{time_text}"
    embed.url = song.url
    if bot.user:
        embed.set_author(name=f"Music Player · {state.filter.upper()} 모드", icon_url=bot.user.display_avatar.url)
    if song.thumbnail:
        embed.set_thumbnail(url=song.thumbnail)
    embed.add_field(name="상태", value=get_playback_status(state), inline=True)
    embed.add_field(name="신청자", value=requester_label(song), inline=True)
    embed.add_field(name="대기열", value=f"{len(state.queue)}곡", inline=True)
    embed.add_field(name="반복", value=LOOP_MODE_NAMES[state.loop_mode], inline=True)
    embed.add_field(name="스킵 투표", value=get_skip_vote_text(state), inline=True)
    embed.add_field(name="볼륨", value=f"음악 {int(state.volume * 100)}% · TTS 중 {int(state.tts_duck_volume * 100)}%", inline=True)
    embed.add_field(name="다음 곡", value=truncate_text(next_song, 80), inline=False)
    return embed

def get_queue_page_count(state):
    return max(1, math.ceil(len(state.queue) / QUEUE_PAGE_SIZE))

def clamp_queue_page(state, page):
    return max(0, min(page, get_queue_page_count(state) - 1))

def build_queue_embed(state, page=0):
    page = clamp_queue_page(state, page)
    page_count = get_queue_page_count(state)
    embed = build_embed(title="📜 음악 대기열", kind="music")

    if state.current_song:
        embed.add_field(
            name="현재 재생",
            value=f"**{truncate_text(state.current_song.title, 90)}**\n신청자: {requester_label(state.current_song)}",
            inline=False
        )

    if not state.queue:
        embed.description = "대기열이 비어 있습니다."
    else:
        start = page * QUEUE_PAGE_SIZE
        visible = state.queue[start:start + QUEUE_PAGE_SIZE]
        lines = []
        for offset, song in enumerate(visible, start=1):
            index = start + offset
            lines.append(
                f"**{index}.** {truncate_text(song.title, 75)} "
                f"`[{format_time(song.duration)}]` · {requester_label(song)}"
            )
        embed.description = "\n".join(lines)

    embed.set_footer(text=f"PuangBOT · 페이지 {page + 1}/{page_count} · 총 {len(state.queue)}곡")
    return embed

async def update_controller_message(guild_id):
    state = get_state(guild_id)
    if not state.controller_msg:
        return
    try:
        await state.controller_msg.edit(embed=build_now_playing_embed(state), view=MusicController(guild_id))
    except Exception as e:
        print(f"컨트롤러 갱신 실패: {e}")
        state.controller_msg = None

def can_skip_immediately(user, state):
    current_song = state.current_song
    requester = getattr(current_song, "requester", None)
    return (
        user.id == OWNER_ID
        or any(role.name.upper() == "DJ" for role in user.roles)
        or (requester is not None and user.id == requester.id)
    )

@bot.event
async def on_voice_state_update(member, before, after):
    if member == bot.user and before.channel and not after.channel:
        guild_id = before.channel.guild.id
        if guild_id in guild_states:
            del guild_states[guild_id] 
            
    if member != bot.user and before.channel:
        if bot.user in before.channel.members:
            if len([m for m in before.channel.members if not m.bot]) == 0:
                vc = before.channel.guild.voice_client
                if vc and vc.is_connected():
                    await vc.disconnect()

class QueueDeleteSelect(discord.ui.Select):
    def __init__(self, guild_id, page):
        self.guild_id = guild_id
        self.page = page
        state = get_state(guild_id)
        start = page * QUEUE_PAGE_SIZE
        visible = state.queue[start:start + QUEUE_PAGE_SIZE]
        options = []
        for offset, song in enumerate(visible):
            index = start + offset
            options.append(discord.SelectOption(
                label=f"{index + 1}. {truncate_text(song.title, 80)}",
                description=f"{format_time(song.duration)} · {requester_label(song)}",
                value=str(index)
            ))

        super().__init__(
            placeholder="삭제할 곡 선택",
            min_values=1,
            max_values=max(1, len(options)),
            options=options,
            row=1,
            disabled=not options
        )

    async def callback(self, interaction: discord.Interaction):
        state = get_state(self.guild_id)
        selected_indices = sorted({int(value) for value in self.values}, reverse=True)
        selected_songs = []
        for index in selected_indices:
            if 0 <= index < len(state.queue):
                selected_songs.append((index, state.queue[index]))

        if not selected_songs:
            await send_status(interaction, "삭제할 곡 없음", "선택한 곡이 이미 대기열에서 사라졌습니다.", "warning", True)
            return

        if not can_manage_music_settings(interaction.user):
            own_songs = all(getattr(song.requester, "id", None) == interaction.user.id for _, song in selected_songs)
            if not own_songs:
                await send_status(interaction, "권한 없음", "DJ/서버 관리자이거나 직접 신청한 곡만 삭제할 수 있습니다.", "error", True)
                return

        lines = [f"- {index + 1}. {truncate_text(song.title, 90)}" for index, song in selected_songs]

        async def do_delete(confirm_interaction):
            state = get_state(self.guild_id)
            removed = []
            for index, song in selected_songs:
                if 0 <= index < len(state.queue) and state.queue[index] is song:
                    removed.append(state.queue.pop(index).title)
                elif song in state.queue:
                    state.queue.remove(song)
                    removed.append(song.title)
            state.queue_page = clamp_queue_page(state, self.page)
            await update_controller_message(self.guild_id)
            embed = build_queue_embed(state, state.queue_page)
            embed.add_field(name="삭제됨", value="\n".join(f"- {truncate_text(title, 80)}" for title in removed) or "없음", inline=False)
            await confirm_interaction.response.edit_message(embed=embed, view=QueueView(self.guild_id, state.queue_page))

        embed = build_status_embed("대기열 삭제 확인", "\n".join(lines), "warning")
        await interaction.response.send_message(
            embed=embed,
            view=ConfirmView(interaction.user.id, do_delete, title="대기열 삭제"),
            ephemeral=True
        )

class QueueView(discord.ui.View):
    def __init__(self, guild_id, page=0):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        state = get_state(guild_id)
        self.page = clamp_queue_page(state, page)
        state.queue_page = self.page
        if state.queue:
            self.add_item(QueueDeleteSelect(guild_id, self.page))
        self._sync_buttons()

    def _sync_buttons(self):
        state = get_state(self.guild_id)
        page_count = get_queue_page_count(state)
        for child in self.children:
            if child.custom_id == "queue_prev":
                child.disabled = self.page <= 0
            elif child.custom_id == "queue_next":
                child.disabled = self.page >= page_count - 1

    async def _edit_queue(self, interaction, page):
        state = get_state(self.guild_id)
        self.page = clamp_queue_page(state, page)
        state.queue_page = self.page
        await interaction.response.edit_message(
            embed=build_queue_embed(state, self.page),
            view=QueueView(self.guild_id, self.page)
        )

    @discord.ui.button(label="이전", emoji="◀️", style=discord.ButtonStyle.secondary, row=0, custom_id="queue_prev")
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._edit_queue(interaction, self.page - 1)

    @discord.ui.button(label="다음", emoji="▶️", style=discord.ButtonStyle.secondary, row=0, custom_id="queue_next")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._edit_queue(interaction, self.page + 1)

    @discord.ui.button(label="새로고침", emoji="🔄", style=discord.ButtonStyle.primary, row=0, custom_id="queue_refresh")
    async def refresh_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._edit_queue(interaction, self.page)

    @discord.ui.button(label="닫기", emoji="✖️", style=discord.ButtonStyle.danger, row=0, custom_id="queue_close")
    async def close_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="대기열 창을 닫았습니다.", embed=None, view=None)

class MusicController(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self._sync_buttons()

    def _sync_buttons(self):
        state = get_state(self.guild_id)
        vc = state.voice_client
        paused = bool(vc and vc.is_paused())
        playing = bool(state.current_song)
        loop_styles = [
            discord.ButtonStyle.secondary,
            discord.ButtonStyle.primary,
            discord.ButtonStyle.success
        ]

        for child in self.children:
            if child.custom_id == "music_pause":
                child.label = "재개" if paused else "일시정지"
                child.emoji = "▶️" if paused else "⏸️"
                child.disabled = not playing
            elif child.custom_id == "music_skip":
                child.disabled = not playing
            elif child.custom_id == "music_stop":
                child.disabled = not (playing or state.queue)
            elif child.custom_id == "music_loop":
                child.label = f"반복: {LOOP_MODE_NAMES[state.loop_mode]}"
                child.style = loop_styles[state.loop_mode]
            elif child.custom_id == "music_shuffle":
                child.disabled = len(state.queue) < 2
            elif child.custom_id == "music_clear":
                child.disabled = not state.queue

    async def _edit_panel(self, interaction):
        state = get_state(self.guild_id)
        await interaction.response.edit_message(
            embed=build_now_playing_embed(state),
            view=MusicController(self.guild_id)
        )

    @discord.ui.button(label="일시정지", emoji="⏸️", style=discord.ButtonStyle.primary, row=0, custom_id="music_pause")
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        if not vc:
            await interaction.response.send_message("재생 중인 노래가 없어요.", ephemeral=True)
            return

        if vc.is_playing():
            vc.pause()
        elif vc.is_paused():
            vc.resume()
        await self._edit_panel(interaction)

    @discord.ui.button(label="스킵", emoji="⏭️", style=discord.ButtonStyle.success, row=0, custom_id="music_skip")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client
        state = get_state(self.guild_id)
        user = interaction.user

        if not vc or not (vc.is_playing() or vc.is_paused()) or not state.current_song:
            await interaction.response.send_message("스킵할 노래가 없어요.", ephemeral=True)
            return

        if not user.voice or user.voice.channel != vc.channel:
            await interaction.response.send_message("❌ 같은 음성 채널에 있어야 스킵할 수 있어요.", ephemeral=True)
            return

        if can_skip_immediately(user, state):
            requester = getattr(state.current_song, "requester", None)
            reason = "신청자 권한" if requester and user.id == requester.id else "DJ 권한"
            state.current_song = None
            vc.stop()
            await interaction.response.send_message(f"⏭️ **{reason}으로 즉시 스킵했습니다!**", ephemeral=True)
            if not state.queue:
                await update_controller_message(self.guild_id)
            return

        channel_members = [m for m in user.voice.channel.members if not m.bot]
        required_votes = max(1, (len(channel_members) + 1) // 2)
        state.skip_votes.add(user.id)

        if len(state.skip_votes) >= required_votes:
            state.current_song = None
            vc.stop()
            await interaction.response.send_message(f"⏭️ **투표 가결 ({len(state.skip_votes)}/{required_votes})!** 스킵합니다.", ephemeral=True)
            if not state.queue:
                await update_controller_message(self.guild_id)
        else:
            await interaction.response.send_message(f"🗳️ **스킵 투표:** {len(state.skip_votes)} / {required_votes}", ephemeral=True)
            await update_controller_message(self.guild_id)

    @discord.ui.button(label="정지", emoji="⏹️", style=discord.ButtonStyle.danger, row=0, custom_id="music_stop")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = get_state(self.guild_id)
        state.queue.clear()
        state.current_song = None
        state.music_source = None
        state.loop_mode = 0
        state.skip_votes.clear()
        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
        await self._edit_panel(interaction)

    @discord.ui.button(label="새로고침", emoji="🔄", style=discord.ButtonStyle.secondary, row=0, custom_id="music_refresh")
    async def refresh_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._edit_panel(interaction)

    @discord.ui.button(label="반복: 끔", emoji="🔁", style=discord.ButtonStyle.secondary, row=1, custom_id="music_loop")
    async def loop_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = get_state(self.guild_id)
        state.loop_mode = (state.loop_mode + 1) % 3
        await self._edit_panel(interaction)

    @discord.ui.button(label="대기열", emoji="📜", style=discord.ButtonStyle.secondary, row=1, custom_id="music_queue")
    async def show_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        state = get_state(self.guild_id)
        page = clamp_queue_page(state, state.queue_page)
        await interaction.response.send_message(
            embed=build_queue_embed(state, page),
            view=QueueView(self.guild_id, page),
            ephemeral=True
        )

    @discord.ui.button(label="셔플", emoji="🔀", style=discord.ButtonStyle.secondary, row=1, custom_id="music_shuffle")
    async def shuffle_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_manage_music_settings(interaction.user):
            await interaction.response.send_message("❌ 서버 관리 권한, DJ 역할, 또는 오너 권한이 필요합니다.", ephemeral=True)
            return

        state = get_state(self.guild_id)
        if len(state.queue) < 2:
            await interaction.response.send_message("❌ 섞을 노래가 2곡 이상 필요합니다.", ephemeral=True)
            return

        random.shuffle(state.queue)
        state.queue_page = clamp_queue_page(state, state.queue_page)
        await self._edit_panel(interaction)

    @discord.ui.button(label="비우기", emoji="🧹", style=discord.ButtonStyle.danger, row=1, custom_id="music_clear")
    async def clear_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not can_manage_music_settings(interaction.user):
            await interaction.response.send_message("❌ 서버 관리 권한, DJ 역할, 또는 오너 권한이 필요합니다.", ephemeral=True)
            return

        state = get_state(self.guild_id)
        state.queue.clear()
        state.queue_page = 0
        await self._edit_panel(interaction)

async def play_next(guild_id, interaction_channel):
    state = get_state(guild_id)
    voice = state.voice_client
    if interaction_channel is not None:
        state.playback_channel = interaction_channel

    if state.current_song and state.loop_mode == 1:
        state.queue.insert(0, state.current_song)
    elif state.current_song and state.loop_mode == 2:
        state.queue.append(state.current_song)

    if not state.queue:
        state.is_playing = False
        state.current_song = None
        if state.controller_msg:
            try:
                await state.controller_msg.edit(embed=build_now_playing_embed(state), view=MusicController(guild_id))
            except Exception:
                state.controller_msg = None
        elif interaction_channel is not None:
            await interaction_channel.send(embed=discord.Embed(description="🎵 모든 노래가 끝났어요!", color=discord.Color.dark_gray()))
        return

    song = state.queue.pop(0)
    state.current_song = song
    state.skip_votes.clear()  # 새 노래가 시작되면 투표 초기화
    state.is_playing = True
    state.start_time = time.time()

    filter_str = FFMPEG_FILTERS.get(state.filter, '')
    ffmpeg_opts = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': f'-vn -filter:a "{filter_str}"' if filter_str else '-vn'
    }

    try:
        # 🌟 이제 절대 경로를 사용하여 ffmpeg를 무조건 찾아냅니다.
        source = discord.FFmpegPCMAudio(song.url, executable=FFMPEG_PATH, **ffmpeg_opts)
        state.music_source = discord.PCMVolumeTransformer(source, volume=state.volume)
        if not start_mixer_if_needed(guild_id, interaction_channel):
            if interaction_channel is not None:
                await interaction_channel.send("❌ 음성 채널 연결이 끊겨 재생할 수 없어요.")
            return

        embed = build_now_playing_embed(state)
        view = MusicController(guild_id)

        if state.controller_msg:
            try:
                await state.controller_msg.edit(embed=embed, view=view)
                return
            except Exception:
                state.controller_msg = None

        if interaction_channel is not None:
            state.controller_msg = await interaction_channel.send(embed=embed, view=view)

    except Exception as e:
        print(f"재생 오류: {e}")
        await play_next(guild_id, interaction_channel)

@bot.event
async def on_ready():
    await bot.tree.sync()
    voice_xp_loop.start() # 봇이 켜지면 음성 채널 경험치 지급 루프 시작
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("🎵 서버 무중단 운영 중"))
    print(f'✅ 푸앙봇 V4.0 로그인 완료! 푸앙푸앙: {bot.user}')

def build_ai_memory_text(message):
    content = strip_bot_mention(message.clean_content or message.content)
    attachment_names = ", ".join(a.filename for a in message.attachments)
    if attachment_names:
        content = (content + "\n" if content else "") + f"[첨부파일: {attachment_names}]"
    return content.strip() or "[내용 없음]"

def build_image_text_fallback_prompt(prompt_text, image_fallbacks):
    fallback_text = "\n\n".join(item for item in image_fallbacks if item).strip()
    if not fallback_text:
        fallback_text = "이미지를 직접 읽지 못했고 OCR/캡션 대체 정보도 없습니다. 사용자가 제공한 텍스트와 첨부 파일명만 근거로 답하세요."
    return f"{prompt_text}\n\n[이미지 대체 분석]\n{fallback_text}"

def add_ai_attempt(attempts, seen, config, profile_id, use_images, prompt_text, reason, task="text"):
    if not profile_id:
        return
    profile = get_ai_model_profile(profile_id, config)
    if use_images and not ai_model_supports(profile, "image"):
        return
    if not ai_model_supports(profile, "text"):
        return
    if not profile_allows_external(profile, task):
        return

    key = (profile["name"], use_images, reason)
    if key in seen:
        return
    seen.add(key)
    attempts.append({
        "profile": profile,
        "use_images": use_images,
        "prompt_text": prompt_text,
        "reason": reason,
        "task": task
    })

def get_profile_fallbacks(profile_id):
    profile = get_ai_model_profile(profile_id)
    return normalize_ai_profile_list(profile.get("fallbacks", []))

def build_ai_attempts(config, prompt_text, image_payloads, image_fallbacks, has_documents=False):
    policy = config.get("fallback_policy", AI_DEFAULT_FALLBACK_POLICY)
    primary_profile = get_ai_primary_model(config)
    fallback_profiles = normalize_ai_profile_list(config.get("fallback_profiles") or config.get("fallback_text_model"))
    vision_profile = normalize_ai_profile_id(config.get("vision_profile") or config.get("fallback_vision_model") or "")
    document_profile = normalize_ai_profile_id(config.get("document_profile") or primary_profile)
    attempts = []
    seen = set()
    primary_fallbacks = get_profile_fallbacks(primary_profile)

    if image_payloads and policy != "text_only":
        for profile_id in unique_ai_model_names(vision_profile, primary_profile, *fallback_profiles, *primary_fallbacks):
            add_ai_attempt(attempts, seen, config, profile_id, True, prompt_text, "이미지 직접 분석", task="image")

    if image_payloads and policy != "strict":
        fallback_prompt = build_image_text_fallback_prompt(prompt_text, image_fallbacks)
        for profile_id in unique_ai_model_names(primary_profile, *fallback_profiles, *primary_fallbacks, AI_DEFAULT_FALLBACK_TEXT_MODEL):
            add_ai_attempt(attempts, seen, config, profile_id, False, fallback_prompt, "이미지 대체 텍스트 분석", task="text")

    if not image_payloads and has_documents:
        for profile_id in unique_ai_model_names(document_profile, primary_profile, *fallback_profiles, *primary_fallbacks, AI_DEFAULT_FALLBACK_TEXT_MODEL):
            add_ai_attempt(attempts, seen, config, profile_id, False, prompt_text, "문서 대화", task="document")

    if not image_payloads and not has_documents:
        for profile_id in unique_ai_model_names(primary_profile, *fallback_profiles, *primary_fallbacks, AI_DEFAULT_FALLBACK_TEXT_MODEL):
            add_ai_attempt(attempts, seen, config, profile_id, False, prompt_text, "텍스트 대화", task="text")

    return attempts

async def run_ai_with_fallback(message, config, prompt_text, image_payloads, image_fallbacks, memory_content, has_documents=False):
    attempts = build_ai_attempts(config, prompt_text, image_payloads, image_fallbacks, has_documents)
    if not attempts:
        if image_payloads:
            raise RuntimeError("이미지를 처리할 수 있는 모델 또는 텍스트 백업 모델이 설정되어 있지 않습니다.")
        raise RuntimeError("사용 가능한 AI 모델 설정이 없습니다.")

    errors = []
    for attempt in attempts:
        profile = attempt["profile"]
        started_at = time.time()
        try:
            answer = await call_ai_model(
                config,
                profile,
                message,
                attempt["prompt_text"],
                image_payloads,
                memory_content,
                use_images=attempt["use_images"]
            )
            append_ai_usage_log(message, profile, attempt.get("task", "text"), True, (time.time() - started_at) * 1000)
            return answer, f"{profile['name']} / {get_ai_provider_display(profile)} / {attempt['reason']}"
        except Exception as error:
            error_type = classify_ai_error(error)
            append_ai_usage_log(message, profile, attempt.get("task", "text"), False, (time.time() - started_at) * 1000, str(error))
            errors.append(f"{profile['name']} ({attempt['reason']}, {error_type}): {error}")

    raise RuntimeError("\n".join(errors[-3:]))

async def probe_ai_model(config, model_name):
    profile = get_ai_model_profile(model_name, config)
    provider = get_ai_provider_for_profile(profile)
    provider_type = provider.get("type", "ollama")
    if not provider.get("enabled", False):
        return f"비활성화됨 / Provider: {provider.get('id')} / 기능: {', '.join(profile.get('capabilities', [])) or 'text'}"
    if provider.get("api_key_env") and not os.getenv(provider["api_key_env"]):
        return f"API 키 없음 / Provider: {provider.get('id')} / Env: {provider['api_key_env']}"

    timeout = aiohttp.ClientTimeout(total=8)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            if provider_type == "openai_compatible":
                url = f"{normalize_ai_base_url(provider.get('base_url'), 'openai_compatible')}/models"
                async with session.get(url, headers=get_provider_headers(provider)) as response:
                    body = await response.text()
                    if response.status >= 400:
                        return f"연결 실패 {response.status}: {body[:160]}"
                    data = json.loads(body)
                    names = [item.get("id") for item in data.get("data", []) if isinstance(item, dict)]
            elif provider_type == "ollama":
                url = f"{normalize_ai_base_url(provider.get('base_url'), 'ollama')}/api/tags"
                async with session.get(url) as response:
                    body = await response.text()
                    if response.status >= 400:
                        return f"연결 실패 {response.status}: {body[:160]}"
                    data = json.loads(body)
                    names = [item.get("name") for item in data.get("models", []) if isinstance(item, dict)]
            else:
                return f"진단 미지원 provider type: {provider_type}"
    except Exception as error:
        return f"연결 실패: {error}"

    installed = profile.get("model", profile["name"]) in names or profile["name"] in names
    caps = ", ".join(profile.get("capabilities", [])) or "text"
    status = "설치됨" if installed else "목록에 없음"
    return f"{status} / Provider: {provider.get('id')} ({provider_type}) / 기능: {caps}"

async def handle_ai_reply(message, config, memory_content):
    async with message.channel.typing():
        base_content = strip_bot_mention(message.clean_content or message.content)
        text_blocks, image_payloads, image_fallbacks, notes = await process_ai_attachments(message.attachments)

        prompt_parts = []
        if base_content:
            prompt_parts.append(base_content)
        if text_blocks:
            prompt_parts.append("\n\n".join(text_blocks))
        if notes:
            prompt_parts.append("[첨부 처리 정보]\n" + "\n".join(notes))
        if not prompt_parts and image_payloads:
            prompt_parts.append("첨부된 이미지를 보고 사용자의 의도를 파악해 답변해 주세요.")

        prompt_text = "\n\n".join(prompt_parts).strip() or "대화를 이어가 주세요."

        try:
            answer, route = await run_ai_with_fallback(
                message,
                config,
                prompt_text,
                image_payloads,
                image_fallbacks,
                memory_content,
                has_documents=bool(text_blocks)
            )
        except Exception as error:
            await message.reply(
                f"❌ 로컬 LLM 호출 실패:\n`{truncate_for_prompt(str(error), 1200)}`",
                mention_author=False
            )
            return

        append_ai_memory(
            AI_LONG_MEMORY_FILE,
            message.guild.id,
            message.channel.id,
            "assistant",
            answer,
            author=bot.user.display_name if bot.user else "PuangBOT"
        )
        append_ai_memory(
            AI_SHORT_MEMORY_FILE,
            message.guild.id,
            message.channel.id,
            "assistant",
            answer,
            author=bot.user.display_name if bot.user else "PuangBOT",
            trim=AI_SHORT_MEMORY_LIMIT
        )

        for index, chunk in enumerate(split_discord_message(answer)):
            if index == 0:
                await message.reply(chunk, mention_author=False)
            else:
                await message.channel.send(chunk)

async def maybe_handle_ai_message(message):
    if not message.guild:
        return

    config = get_ai_channel_config(message.guild.id, message.channel.id)
    if not config.get("enabled"):
        return

    memory_content = build_ai_memory_text(message)
    attachments = summarize_attachments_for_memory(message.attachments)
    append_ai_memory(
        AI_LONG_MEMORY_FILE,
        message.guild.id,
        message.channel.id,
        "user",
        memory_content,
        author=message.author.display_name,
        attachments=attachments
    )
    append_ai_memory(
        AI_SHORT_MEMORY_FILE,
        message.guild.id,
        message.channel.id,
        "user",
        memory_content,
        author=message.author.display_name,
        attachments=attachments,
        trim=AI_SHORT_MEMORY_LIMIT
    )

    if is_ai_triggered(message, config):
        asyncio.create_task(handle_ai_reply(message, config, memory_content))

# 💡 채팅을 치면 경험치 획득 (글자 수에 비례하되 최대 20 제한)
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot: return

    # --- [수정: 개인별 TTS 감지 및 옵션 적용 로직] ---
    tts_data = load_tts()
    uid = str(message.author.id)
    user_settings = tts_data.get(uid, {})
    
    if user_settings.get("enabled", False) and message.author.voice:
        guild_id = message.guild.id
        state = get_state(guild_id)
        
        if not message.guild.voice_client:
            await message.author.voice.channel.connect(timeout=20.0, self_deaf=True)
            state.voice_client = message.guild.voice_client
            
        say_name = user_settings.get("say_name", "yes")
        
        if say_name == "yes":
            if state.last_tts_user == message.author.id:
                text_to_read = message.content 
            else:
                text_to_read = f"{message.author.display_name}님의 말. {message.content}"
        else:
            text_to_read = message.content
            
        state.last_tts_user = message.author.id 
        
        # 엔진과 부가 설정을 큐에 담아서 전송 (엔진 기본값은 gtts)
        payload = {
            "text": text_to_read,
            "engine": user_settings.get("engine", "gtts"),
            "voice": user_settings.get("voice", "ko-KR-SunHiNeural"),
            "pitch": user_settings.get("pitch", "+0Hz")
        }
        await state.tts_queue.put(payload)
        
        if state.tts_task is None or state.tts_task.done():
            state.tts_task = asyncio.create_task(process_tts_queue(message.guild))
    # -----------------------------------

    await maybe_handle_ai_message(message)

    gained_xp = min(20, max(5, len(message.content)))
    await add_xp(message.author, gained_xp, message.channel)

    await bot.process_commands(message)

# 💡 음성 채널에 머물면 경험치 획득 (5분마다 실행되는 백그라운드 태스크)
@tasks.loop(minutes=5.0)
async def voice_xp_loop():
    for guild in bot.guilds:
        for vc in guild.voice_channels:
            # 음성 채널에 봇을 제외하고 사람이 있다면
            members = [m for m in vc.members if not m.bot]
            if members:
                for member in members:
                    # 음악을 듣거나 통화 중인 유저에게 꾸준히 30 XP 지급
                    # (여기서는 채팅창 도배 방지를 위해 채널 객체를 넘기지 않아 레벨업 메시지는 생략됩니다)
                    await add_xp(member, 30)

# ==========================================
# 🤖 서버 관제 명령어 (자동 완성 포함)
# ==========================================

# 1. mc 폴더 내의 폴더 리스트를 실시간으로 불러오는 자동 완성 함수
async def server_list_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    # 1. 경로가 실제로 존재하는지 먼저 검사
    if not os.path.exists(MC_ROOT_DIR):
        return [app_commands.Choice(name="⚠️ 경로 오류 (server/mc 폴더 없음)", value="error")]
    
    try:
        # 2. 폴더 목록 가져오기
        folders = [f for f in os.listdir(MC_ROOT_DIR) if os.path.isdir(os.path.join(MC_ROOT_DIR, f))]
        
        # 3. 검색어 필터링
        choices = [
            app_commands.Choice(name=folder, value=folder)
            for folder in folders if current.lower() in folder.lower()
        ]
        
        return choices[:25] # 디스코드 최대 25개 제한
    except Exception as e:
        print(f"❌ 자동 완성 오류: {e}")
        return []

def is_windows_process_running(image_name):
    if platform.system() != "Windows":
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image_name}"],
            capture_output=True,
            text=True,
            creationflags=0x08000000
        )
        return image_name.lower() in (result.stdout or "").lower()
    except Exception:
        return False

def get_server_folders():
    if not os.path.exists(MC_ROOT_DIR):
        return []
    return [
        name for name in os.listdir(MC_ROOT_DIR)
        if os.path.isdir(os.path.join(MC_ROOT_DIR, name))
    ]

def build_server_status_embed():
    folders = get_server_folders()
    playit_path = os.path.join(PLAYIT_DIR, PLAYIT_LINK)
    java_running = is_windows_process_running("java.exe") or is_windows_process_running("javaw.exe")
    playit_running = is_windows_process_running("playit.exe") or is_windows_process_running("playit.gg.exe")
    embed = build_embed(title="🖥️ 서버 상태", kind="server")
    embed.add_field(name="마크 서버 폴더", value=f"{len(folders)}개" if folders else "없음 또는 경로 없음", inline=True)
    embed.add_field(name="Java 프로세스", value="감지됨" if java_running else "감지 안 됨", inline=True)
    embed.add_field(name="Playit 프로세스", value="감지됨" if playit_running else "감지 안 됨", inline=True)
    embed.add_field(name="마크 루트", value=f"`{MC_ROOT_DIR}`", inline=False)
    embed.add_field(name="Playit 바로가기", value="있음" if os.path.exists(playit_path) else f"없음\n`{playit_path}`", inline=False)

    try:
        with MCRcon("127.0.0.1", RCON_PASSWORD, port=25575) as mcr:
            response = mcr.command("list")
        embed.add_field(name="RCON", value=f"연결됨\n`{truncate_text(response, 180)}`", inline=False)
    except Exception as e:
        embed.add_field(name="RCON", value=f"연결 실패\n`{truncate_text(e, 180)}`", inline=False)

    if folders:
        embed.add_field(name="서버 목록", value="\n".join(f"- {truncate_text(name, 60)}" for name in folders[:10]), inline=False)
    return embed

@bot.tree.command(name="서버상태", description="[관리자] 마인크래프트 서버와 Playit 상태를 확인합니다.")
async def server_status(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 오너만 사용할 수 있습니다.", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_server_status_embed(), ephemeral=True)

@bot.tree.command(name="서버켜기", description="[관리자] mc 폴더 내의 서버를 선택하여 실행합니다.")
@app_commands.autocomplete(server_name=server_list_autocomplete)
async def start_selected_server(interaction: discord.Interaction, server_name: str):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 오너만 사용할 수 있습니다.", ephemeral=True)
        return

    target_dir = os.path.join(MC_ROOT_DIR, server_name)
    bat_path = os.path.join(target_dir, "start.bat")

    if not os.path.exists(bat_path):
        await interaction.response.send_message(f"❌ `{server_name}` 폴더에 `start.bat`이 없습니다!", ephemeral=True)
        return

    await interaction.response.send_message(f"🚀 **{server_name}** 서버의 `start.bat`을 백그라운드에서 실행합니다...")
    
    try:
        # 윈도우에서 독립된 프로세스로 실행 (서버가 켜져도 봇이 멈추지 않음)
        subprocess.Popen(
            ["start.bat"],
            cwd=target_dir,
            creationflags=0x00000008, # DETACHED_PROCESS
            shell=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ 실행 에러: {e}")

@bot.tree.command(name="통로열기", description="[관리자] playit.gg 바로가기를 실행합니다.")
async def open_tunnel(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 권한이 없습니다.", ephemeral=True)
        return

    target_path = os.path.join(PLAYIT_DIR, PLAYIT_LINK)
    
    if not os.path.exists(target_path):
        await interaction.response.send_message(f"❌ `{target_path}` 파일을 찾을 수 없습니다. 이름(playit.gg.lnk)을 확인해주세요.", ephemeral=True)
        return

    await interaction.response.send_message("🌐 **Playit.gg 통로를 개방합니다...**")
    try:
        os.startfile(target_path) # 윈도우 바로가기 실행
    except Exception as e:
        await interaction.followup.send(f"❌ 실행 에러: {e}")

@bot.tree.command(name="시스템재부팅", description="[관리자] 컴퓨터 시스템을 즉시 재시작합니다.")
async def reboot_system(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 위험한 명령어입니다. 오너만 가능합니다.", ephemeral=True)
        return

    async def do_reboot(confirm_interaction):
        await confirm_interaction.response.edit_message(
            embed=build_status_embed("시스템 재부팅 예약", "10초 뒤 컴퓨터를 재부팅합니다. 저장되지 않은 작업은 종료됩니다.", "warning"),
            view=None
        )
        await asyncio.sleep(10)
        try:
            if platform.system() == "Windows":
                os.system("shutdown /r /t 1")
            else:
                await confirm_interaction.followup.send("❌ 윈도우 시스템이 아닙니다.", ephemeral=True)
        except Exception as e:
            await confirm_interaction.followup.send(f"❌ 명령 실패: {e}", ephemeral=True)

    await interaction.response.send_message(
        embed=build_status_embed("시스템 재부팅 확인", "이 작업은 현재 컴퓨터를 재부팅합니다. 계속할까요?", "warning"),
        view=ConfirmView(interaction.user.id, do_reboot, title="시스템 재부팅"),
        ephemeral=True
    )

@bot.tree.command(name="서버끄기", description="[관리자] 현재 켜져 있는 마인크래프트 서버를 안전하게 종료합니다.")
async def stop_server(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 오너만 사용할 수 있습니다.", ephemeral=True)
        return

    async def do_stop(confirm_interaction):
        await confirm_interaction.response.edit_message(
            embed=build_status_embed("서버 종료 진행 중", "RCON으로 5초 안내 후 `stop` 명령을 전송합니다.", "warning"),
            view=None
        )
        try:
            with MCRcon("127.0.0.1", RCON_PASSWORD, port=25575) as mcr:
                mcr.command("say [푸앙봇] 5초 뒤 서버가 종료됩니다! 데이터가 저장됩니다.")
                await asyncio.sleep(5)
                mcr.command("stop")
            await confirm_interaction.followup.send("✅ **서버 종료 명령 전송 완료!** 완전히 꺼질 때까지 잠시 대기해주세요.", ephemeral=True)
        except Exception as e:
            await confirm_interaction.followup.send(f"❌ **종료 실패:** 서버가 켜져 있지 않거나 RCON이 연결되지 않았습니다.\n`{e}`", ephemeral=True)

    await interaction.response.send_message(
        embed=build_status_embed("서버 종료 확인", "현재 켜져 있는 마인크래프트 서버를 안전하게 종료할까요?", "warning"),
        view=ConfirmView(interaction.user.id, do_stop, title="서버 종료"),
        ephemeral=True
    )

@bot.tree.command(name="통로끊기", description="[관리자] Playit.gg 터널링 프로세스를 종료합니다.")
async def close_tunnel(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 오너만 사용할 수 있습니다.", ephemeral=True)
        return

    async def do_close(confirm_interaction):
        await confirm_interaction.response.edit_message(
            embed=build_status_embed("통로 종료 진행 중", "Playit.gg 프로세스를 종료합니다.", "warning"),
            view=None
        )
        try:
            if platform.system() == "Windows":
                os.system("taskkill /F /IM playit* /T")
                await confirm_interaction.followup.send("✅ **통로가 성공적으로 닫혔습니다.**", ephemeral=True)
            else:
                await confirm_interaction.followup.send("❌ 윈도우 환경에서만 지원되는 명령어입니다.", ephemeral=True)
        except Exception as e:
            await confirm_interaction.followup.send(f"❌ 프로세스 종료 실패: {e}", ephemeral=True)

    await interaction.response.send_message(
        embed=build_status_embed("Playit 통로 종료 확인", "현재 Playit.gg 터널링 프로세스를 강제로 종료할까요?", "warning"),
        view=ConfirmView(interaction.user.id, do_close, title="통로 종료"),
        ephemeral=True
    )

def format_ai_profile_summary(profile_id):
    if not profile_id:
        return "`없음`"
    profile = get_ai_model_profile(profile_id)
    provider = get_ai_provider_for_profile(profile)
    caps = ", ".join(profile.get("capabilities", [])) or "text"
    privacy = "외부 API" if profile.get("privacy") == "external" or provider.get("privacy") == "external" else "로컬"
    label = profile.get("label", profile["name"])
    enabled = "사용 가능" if provider.get("enabled") else "provider 꺼짐"
    return f"**{label}** (`{profile['name']}`)\n{privacy} · {provider.get('id')} · {caps} · {enabled}"

def format_ai_profile_list(profile_ids):
    profile_ids = normalize_ai_profile_list(profile_ids)
    if not profile_ids:
        return "`없음`"
    return "\n".join(f"- `{profile_id}`" for profile_id in profile_ids)

def build_ai_panel_embed(guild_id, channel):
    config = get_ai_channel_config(guild_id, channel.id)
    profile = get_ai_model_profile(get_ai_primary_model(config), config)
    mode_name = "상시 대화" if config.get("mode") == "always" else "멘션 기반"
    short_count = count_ai_memory(AI_SHORT_MEMORY_FILE, guild_id, channel.id)
    long_count = count_ai_memory(AI_LONG_MEMORY_FILE, guild_id, channel.id)
    embed = build_embed(
        title="🤖 AI 패널",
        description=f"{channel.mention} 채널의 AI 모델 선택 패널입니다. Provider/API 키/URL은 서버 설정 파일에서만 관리합니다.",
        kind="ai" if config.get("enabled") else "neutral"
    )
    embed.add_field(name="상태", value="켜짐" if config.get("enabled") else "꺼짐", inline=True)
    embed.add_field(name="모드", value=mode_name, inline=True)
    embed.add_field(name="라우팅", value=f"`{config.get('route_policy', 'selected_first')}`", inline=True)
    embed.add_field(name="기본 프로필", value=format_ai_profile_summary(config.get("selected_profile")), inline=False)
    embed.add_field(name="이미지 프로필", value=format_ai_profile_summary(config.get("vision_profile")), inline=False)
    embed.add_field(name="문서 프로필", value=format_ai_profile_summary(config.get("document_profile")), inline=False)
    embed.add_field(name="백업 프로필", value=format_ai_profile_list(config.get("fallback_profiles")), inline=False)
    embed.add_field(
        name="응답 전송",
        value=f"`{config.get('reply_mode', 'auto')}` · {config.get('reply_inline_limit', AI_REPLY_INLINE_LIMIT)}자 초과 파일 · {get_ai_max_tokens(profile, config)} 토큰",
        inline=False
    )
    embed.add_field(name="기억", value=f"단기 {short_count}개 · 장기 {long_count}개", inline=False)
    return embed

def profile_matches_capability(profile, capability):
    if not capability:
        return True
    if capability == "document":
        return "document" in profile.get("capabilities", []) or "text" in profile.get("capabilities", [])
    return capability in profile.get("capabilities", [])

def get_ai_model_options(include_none=False, capability=None, group=None):
    options = []
    if include_none:
        options.append(discord.SelectOption(label="없음", value="__none__", description="이 백업 모델을 사용하지 않습니다."))
    for name, profile in list(get_ai_models().get("profiles", {}).items()):
        if len(options) >= 25:
            break
        if not profile.get("visible", True) or not profile.get("selectable", False):
            continue
        if group and profile.get("group") != group:
            continue
        if not profile_matches_capability(profile, capability):
            continue
        provider = get_ai_provider_for_profile(profile)
        caps = ", ".join(profile.get("capabilities", [])) or "text"
        privacy = "API" if profile.get("privacy") == "external" or provider.get("privacy") == "external" else "로컬"
        label = profile.get("label") or name
        options.append(discord.SelectOption(
            label=truncate_text(label, 100),
            value=name,
            description=truncate_text(f"{name} · {privacy} · {caps}", 100)
        ))
    return options

def is_selectable_ai_profile(profile_id, capability=None, allow_empty=False):
    if allow_empty and not profile_id:
        return True
    profile_id = normalize_ai_profile_id(profile_id)
    profile = get_ai_models().get("profiles", {}).get(profile_id)
    return bool(
        profile
        and profile.get("selectable", False)
        and profile_matches_capability(profile, capability)
    )

class AIModelSelect(discord.ui.Select):
    def __init__(self, guild_id, channel, target, placeholder, include_none=False, capability=None, row=None, multi=False):
        self.guild_id = guild_id
        self.channel = channel
        self.target = target
        options = get_ai_model_options(include_none=include_none, capability=capability)
        max_values = min(3, len([option for option in options if option.value != "__none__"])) if multi else 1
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=max(1, max_values),
            options=options,
            row=row,
            disabled=not options
        )

    async def callback(self, interaction: discord.Interaction):
        values = [value for value in self.values if value != "__none__"]
        value = values[0] if values else ""
        if self.target == "fallback_profiles":
            updates = {"fallback_profiles": values}
        else:
            updates = {self.target: value}
        if self.target == "selected_profile":
            updates["primary_model"] = value
            updates["model"] = value
        set_ai_channel_config(self.guild_id, self.channel.id, **updates)
        await interaction.response.edit_message(
            embed=build_ai_panel_embed(self.guild_id, self.channel),
            view=AIPanelView(self.guild_id, self.channel)
        )

class AIPanelView(discord.ui.View):
    def __init__(self, guild_id, channel):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.channel = channel
        self.add_item(AIModelSelect(guild_id, channel, "selected_profile", "기본 모델 프로필 선택", capability="text", row=1))
        self.add_item(AIModelSelect(guild_id, channel, "vision_profile", "이미지 모델 프로필 선택", include_none=True, capability="image", row=2))
        self.add_item(AIModelSelect(guild_id, channel, "document_profile", "문서 모델 프로필 선택", capability="document", row=3))
        self.add_item(AIModelSelect(guild_id, channel, "fallback_profiles", "백업 프로필 선택", include_none=True, capability="text", row=4, multi=True))
        self._sync_buttons()

    def _sync_buttons(self):
        config = get_ai_channel_config(self.guild_id, self.channel.id)
        for child in self.children:
            if getattr(child, "custom_id", None) == "ai_toggle":
                child.label = "끄기" if config.get("enabled") else "켜기"
                child.style = discord.ButtonStyle.danger if config.get("enabled") else discord.ButtonStyle.success
            elif getattr(child, "custom_id", None) == "ai_mode":
                child.label = "상시 대화" if config.get("mode") != "always" else "멘션 기반"

    async def interaction_check(self, interaction: discord.Interaction):
        if not can_manage_ai_settings(interaction.user):
            await send_status(interaction, "권한 없음", "서버 관리 권한 또는 오너 권한이 필요합니다.", "error", True)
            return False
        return True

    @discord.ui.button(label="켜기", emoji="🔌", style=discord.ButtonStyle.success, row=0, custom_id="ai_toggle")
    async def toggle_ai(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = get_ai_channel_config(self.guild_id, self.channel.id)
        set_ai_channel_config(self.guild_id, self.channel.id, enabled=not config.get("enabled"))
        await interaction.response.edit_message(embed=build_ai_panel_embed(self.guild_id, self.channel), view=AIPanelView(self.guild_id, self.channel))

    @discord.ui.button(label="상시 대화", emoji="💬", style=discord.ButtonStyle.primary, row=0, custom_id="ai_mode")
    async def toggle_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = get_ai_channel_config(self.guild_id, self.channel.id)
        next_mode = "mention" if config.get("mode") == "always" else "always"
        set_ai_channel_config(self.guild_id, self.channel.id, mode=next_mode)
        await interaction.response.edit_message(embed=build_ai_panel_embed(self.guild_id, self.channel), view=AIPanelView(self.guild_id, self.channel))

    @discord.ui.button(label="진단", emoji="🩺", style=discord.ButtonStyle.secondary, row=0, custom_id="ai_diagnose_panel")
    async def diagnose(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = get_ai_channel_config(self.guild_id, self.channel.id)
        await interaction.response.defer(ephemeral=True)
        lines = []
        for profile_id in unique_ai_model_names(
            config.get("selected_profile"),
            config.get("vision_profile"),
            config.get("document_profile"),
            *normalize_ai_profile_list(config.get("fallback_profiles"))
        ):
            lines.append(f"`{profile_id}`: {await probe_ai_model(config, profile_id)}")
        embed = build_embed(title="AI 진단", description="\n".join(lines) if lines else "설정된 모델이 없습니다.", kind="ai")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="새로고침", emoji="🔄", style=discord.ButtonStyle.secondary, row=0, custom_id="ai_refresh")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=build_ai_panel_embed(self.guild_id, self.channel), view=AIPanelView(self.guild_id, self.channel))

@bot.tree.command(name="ai패널", description="채널 AI 설정을 버튼과 선택 메뉴로 관리합니다.")
@app_commands.describe(채널="AI 패널을 열 채널입니다. 비워두면 현재 채널을 사용합니다.")
async def ai_panel(interaction: discord.Interaction, 채널: discord.TextChannel = None):
    if not can_manage_ai_settings(interaction.user):
        await interaction.response.send_message("❌ 서버 관리 권한 또는 오너 권한이 필요합니다.", ephemeral=True)
        return

    target_channel = 채널 or interaction.channel
    get_ai_channel_config(interaction.guild_id, target_channel.id, create=True)
    await interaction.response.send_message(
        embed=build_ai_panel_embed(interaction.guild_id, target_channel),
        view=AIPanelView(interaction.guild_id, target_channel),
        ephemeral=True
    )

@bot.tree.command(name="ai켜기", description="이 채널 또는 지정 채널에서 로컬 LLM 대화를 켭니다.")
@app_commands.describe(
    채널="AI 대화를 켤 채널입니다. 비워두면 현재 채널에 적용됩니다.",
    모드="멘션할 때만 답할지, 모든 일반 메시지에 답할지 선택합니다.",
    프로필="서버에 등록된 기본 모델 프로필 ID입니다. 예: local-fast",
    이미지프로필="이미지를 직접 읽을 프로필 ID입니다. 예: local-vision",
    문서프로필="문서를 처리할 프로필 ID입니다. 예: local-fast",
    백업프로필="기본 모델 실패 시 사용할 백업 프로필 ID입니다.",
    백업정책="모델 실패 또는 이미지 미지원 시 대체 실행 방식을 선택합니다."
)
@app_commands.choices(
    모드=[
        app_commands.Choice(name="멘션할 때만 답변", value="mention"),
        app_commands.Choice(name="상시 대화", value="always")
    ],
    백업정책=[
        app_commands.Choice(name="안전 백업: 비전 실패 시 텍스트 대체", value="safe_degrade"),
        app_commands.Choice(name="텍스트만: 이미지는 OCR/메타데이터로 처리", value="text_only"),
        app_commands.Choice(name="엄격: 직접 처리 가능한 모델만 사용", value="strict")
    ]
)
async def ai_enable(
    interaction: discord.Interaction,
    채널: discord.TextChannel = None,
    모드: str = "mention",
    프로필: str = AI_DEFAULT_MODEL,
    이미지프로필: str = AI_DEFAULT_FALLBACK_VISION_MODEL,
    문서프로필: str = AI_DEFAULT_DOCUMENT_MODEL,
    백업프로필: str = AI_DEFAULT_FALLBACK_TEXT_MODEL,
    백업정책: str = AI_DEFAULT_FALLBACK_POLICY
):
    if not can_manage_ai_settings(interaction.user):
        await interaction.response.send_message("❌ 서버 관리 권한 또는 오너 권한이 필요합니다.", ephemeral=True)
        return

    profile_id = normalize_ai_profile_id(프로필)
    vision_profile = normalize_ai_profile_id(이미지프로필)
    document_profile = normalize_ai_profile_id(문서프로필)
    fallback_profile = normalize_ai_profile_id(백업프로필)
    validation_errors = []
    if not is_selectable_ai_profile(profile_id, "text"):
        validation_errors.append(f"기본 프로필 `{profile_id}`")
    if vision_profile and not is_selectable_ai_profile(vision_profile, "image", allow_empty=True):
        validation_errors.append(f"이미지 프로필 `{vision_profile}`")
    if document_profile and not is_selectable_ai_profile(document_profile, "document"):
        validation_errors.append(f"문서 프로필 `{document_profile}`")
    if fallback_profile and not is_selectable_ai_profile(fallback_profile, "text"):
        validation_errors.append(f"백업 프로필 `{fallback_profile}`")
    if validation_errors:
        await interaction.response.send_message(
            "❌ 서버에 등록된 선택 가능 프로필만 사용할 수 있습니다.\n"
            + "\n".join(f"- {item}" for item in validation_errors),
            ephemeral=True
        )
        return

    target_channel = 채널 or interaction.channel
    config = set_ai_channel_config(
        interaction.guild_id,
        target_channel.id,
        enabled=True,
        mode=모드,
        selected_profile=profile_id,
        vision_profile=vision_profile,
        document_profile=document_profile,
        fallback_profiles=[fallback_profile] if fallback_profile else [],
        fallback_policy=백업정책
    )
    mode_name = "상시 대화" if config["mode"] == "always" else "멘션 기반"
    await interaction.response.send_message(
        f"✅ {target_channel.mention}에서 AI 대화를 켰습니다.\n"
        f"- 모드: **{mode_name}**\n"
        f"- 기본 프로필: `{config['selected_profile']}`\n"
        f"- 이미지 프로필: `{config['vision_profile'] or '없음'}`\n"
        f"- 문서 프로필: `{config['document_profile'] or '없음'}`\n"
        f"- 백업 프로필: `{', '.join(config['fallback_profiles']) or '없음'}`\n"
        f"- 백업 정책: `{config['fallback_policy']}`\n"
        f"- Provider/API 설정은 서버 내부 파일에서 관리됩니다.",
        ephemeral=True
    )

@bot.tree.command(name="ai끄기", description="이 채널 또는 지정 채널의 로컬 LLM 대화를 끕니다.")
@app_commands.describe(채널="AI 대화를 끌 채널입니다. 비워두면 현재 채널에 적용됩니다.")
async def ai_disable(interaction: discord.Interaction, 채널: discord.TextChannel = None):
    if not can_manage_ai_settings(interaction.user):
        await interaction.response.send_message("❌ 서버 관리 권한 또는 오너 권한이 필요합니다.", ephemeral=True)
        return

    target_channel = 채널 or interaction.channel
    set_ai_channel_config(interaction.guild_id, target_channel.id, enabled=False)
    await interaction.response.send_message(f"🔇 {target_channel.mention}의 AI 대화를 껐습니다.", ephemeral=True)

@bot.tree.command(name="ai상태", description="이 채널 또는 지정 채널의 AI 설정과 기억 상태를 확인합니다.")
@app_commands.describe(채널="확인할 채널입니다. 비워두면 현재 채널을 확인합니다.")
async def ai_status(interaction: discord.Interaction, 채널: discord.TextChannel = None):
    target_channel = 채널 or interaction.channel
    config = get_ai_channel_config(interaction.guild_id, target_channel.id)
    mode_name = "상시 대화" if config.get("mode") == "always" else "멘션 기반"
    short_count = count_ai_memory(AI_SHORT_MEMORY_FILE, interaction.guild_id, target_channel.id)
    long_count = count_ai_memory(AI_LONG_MEMORY_FILE, interaction.guild_id, target_channel.id)
    profile = get_ai_model_profile(get_ai_primary_model(config), config)
    caps = ", ".join(profile.get("capabilities", [])) or "text"
    embed = discord.Embed(title="🤖 AI 상태", color=discord.Color.green() if config.get("enabled") else discord.Color.dark_gray())
    embed.add_field(name="채널", value=target_channel.mention, inline=True)
    embed.add_field(name="상태", value="켜짐" if config.get("enabled") else "꺼짐", inline=True)
    embed.add_field(name="모드", value=mode_name, inline=True)
    embed.add_field(name="기본 프로필", value=f"`{config.get('selected_profile', AI_DEFAULT_MODEL)}` ({caps})", inline=False)
    embed.add_field(name="이미지 프로필", value=f"`{config.get('vision_profile') or '없음'}`", inline=True)
    embed.add_field(name="문서 프로필", value=f"`{config.get('document_profile') or '없음'}`", inline=True)
    embed.add_field(name="백업 프로필", value=format_ai_profile_list(config.get("fallback_profiles")), inline=False)
    embed.add_field(name="백업 정책", value=f"`{config.get('fallback_policy', AI_DEFAULT_FALLBACK_POLICY)}`", inline=True)
    embed.add_field(name="Provider", value=get_ai_provider_display(profile), inline=False)
    embed.add_field(name="응답 전송", value=f"`{config.get('reply_mode', 'auto')}` / {config.get('reply_inline_limit', AI_REPLY_INLINE_LIMIT)}자 초과 파일", inline=True)
    embed.add_field(name="생성 제한", value=f"{get_ai_max_tokens(profile, config)} 토큰", inline=True)
    embed.add_field(name="단기 기억", value=f"{short_count}개", inline=True)
    embed.add_field(name="장기 기억", value=f"{long_count}개", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ai응답설정", description="AI 긴 답변 전송 방식과 생성 길이 제한을 설정합니다.")
@app_commands.describe(
    채널="설정을 바꿀 채널입니다. 비워두면 현재 채널에 적용됩니다.",
    방식="긴 답변을 처리하는 방식입니다.",
    긴답변기준="자동 모드에서 이 글자 수를 넘으면 파일로 첨부합니다. 최대: 1900",
    최대생성토큰="모델이 생성할 최대 토큰 수입니다. Gemma4 권장: 4096"
)
@app_commands.choices(
    방식=[
        app_commands.Choice(name="자동: 짧으면 메시지, 길면 파일", value="auto"),
        app_commands.Choice(name="항상 파일 첨부", value="file"),
        app_commands.Choice(name="메시지 분할", value="split")
    ]
)
async def ai_response_settings(
    interaction: discord.Interaction,
    채널: discord.TextChannel = None,
    방식: str = "auto",
    긴답변기준: int = AI_REPLY_INLINE_LIMIT,
    최대생성토큰: int = AI_DEFAULT_MAX_TOKENS
):
    if not can_manage_ai_settings(interaction.user):
        await interaction.response.send_message("❌ 서버 관리 권한 또는 오너 권한이 필요합니다.", ephemeral=True)
        return

    inline_limit = clamp_discord_inline_limit(긴답변기준)
    max_tokens = max(256, min(8192, int(최대생성토큰)))
    target_channel = 채널 or interaction.channel
    config = set_ai_channel_config(
        interaction.guild_id,
        target_channel.id,
        reply_mode=방식,
        reply_inline_limit=inline_limit,
        max_tokens=max_tokens
    )
    await interaction.response.send_message(
        f"✅ {target_channel.mention} AI 응답 설정을 저장했습니다.\n"
        f"- 전송 방식: `{config['reply_mode']}`\n"
        f"- 긴 답변 기준: `{config['reply_inline_limit']}`자\n"
        f"- 최대 생성 토큰: `{config['max_tokens']}`",
        ephemeral=True
    )

@bot.tree.command(name="ai모델목록", description="등록된 로컬 LLM 모델 프로필과 기능을 확인합니다.")
async def ai_model_list(interaction: discord.Interaction):
    models = get_ai_models().get("profiles", {})
    embed = discord.Embed(
        title="🧠 AI 모델 프로필",
        description=f"표시 가능한 프로필 목록입니다. Provider/API 키/URL은 서버 내부 파일에서 관리합니다.",
        color=discord.Color.blurple()
    )
    visible_profiles = [(name, profile) for name, profile in models.items() if profile.get("visible", True)]
    for name, profile in visible_profiles[:18]:
        provider = get_ai_provider_for_profile(profile)
        caps = ", ".join(profile.get("capabilities", [])) or "text"
        privacy = "외부 API" if profile.get("privacy") == "external" or provider.get("privacy") == "external" else "로컬"
        selectable = "선택 가능" if profile.get("selectable", False) else "목록 표시만"
        note = profile.get("note", "")
        value = (
            f"ID: `{name}`\n"
            f"Provider: `{provider.get('id')}` / Model: `{profile.get('model', name)}`\n"
            f"{privacy} · {selectable} · 기능: `{caps}`"
        )
        if note:
            value += f"\n{note}"
        embed.add_field(name=name, value=value[:1024], inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ai모델설정", description="채널별 AI 프로필을 서버 등록 목록에서 선택합니다.")
@app_commands.describe(
    채널="설정을 바꿀 채널입니다. 비워두면 현재 채널에 적용됩니다.",
    기본프로필="기본 대화 프로필 ID입니다.",
    이미지프로필="이미지를 직접 읽을 프로필 ID입니다.",
    문서프로필="문서를 처리할 프로필 ID입니다.",
    백업프로필="기본 모델 실패 시 사용할 백업 프로필 ID입니다."
)
async def ai_model_set(
    interaction: discord.Interaction,
    채널: discord.TextChannel = None,
    기본프로필: str = "",
    이미지프로필: str = "",
    문서프로필: str = "",
    백업프로필: str = ""
):
    if not can_manage_ai_settings(interaction.user):
        await interaction.response.send_message("❌ 서버 관리 권한 또는 오너 권한이 필요합니다.", ephemeral=True)
        return

    target_channel = 채널 or interaction.channel
    updates = {}
    validation_errors = []
    if 기본프로필.strip():
        profile_id = normalize_ai_profile_id(기본프로필)
        if not is_selectable_ai_profile(profile_id, "text"):
            validation_errors.append(f"기본 프로필 `{profile_id}`")
        updates["selected_profile"] = profile_id
    if 이미지프로필.strip():
        profile_id = normalize_ai_profile_id(이미지프로필)
        if not is_selectable_ai_profile(profile_id, "image"):
            validation_errors.append(f"이미지 프로필 `{profile_id}`")
        updates["vision_profile"] = profile_id
    if 문서프로필.strip():
        profile_id = normalize_ai_profile_id(문서프로필)
        if not is_selectable_ai_profile(profile_id, "document"):
            validation_errors.append(f"문서 프로필 `{profile_id}`")
        updates["document_profile"] = profile_id
    if 백업프로필.strip():
        profile_id = normalize_ai_profile_id(백업프로필)
        if not is_selectable_ai_profile(profile_id, "text"):
            validation_errors.append(f"백업 프로필 `{profile_id}`")
        updates["fallback_profiles"] = [profile_id]

    if validation_errors:
        await interaction.response.send_message(
            "❌ 서버에 등록된 선택 가능 프로필만 사용할 수 있습니다.\n"
            + "\n".join(f"- {item}" for item in validation_errors),
            ephemeral=True
        )
        return

    if not updates:
        await interaction.response.send_message("변경할 값을 하나 이상 입력해 주세요.", ephemeral=True)
        return

    config = set_ai_channel_config(interaction.guild_id, target_channel.id, **updates)
    await interaction.response.send_message(
        f"✅ {target_channel.mention} AI 프로필 설정을 저장했습니다.\n"
        f"- 기본 프로필: `{config['selected_profile']}`\n"
        f"- 이미지 프로필: `{config['vision_profile'] or '없음'}`\n"
        f"- 문서 프로필: `{config['document_profile'] or '없음'}`\n"
        f"- 백업 프로필: `{', '.join(config['fallback_profiles']) or '없음'}`",
        ephemeral=True
    )

@bot.tree.command(name="ai백업설정", description="AI 모델 실패 시 백업 실행 정책을 변경합니다.")
@app_commands.describe(
    채널="설정을 바꿀 채널입니다. 비워두면 현재 채널에 적용됩니다.",
    정책="이미지/모델 실패 시 대체 실행 방식입니다."
)
@app_commands.choices(
    정책=[
        app_commands.Choice(name="안전 백업: 비전 실패 시 텍스트 대체", value="safe_degrade"),
        app_commands.Choice(name="텍스트만: 이미지는 OCR/메타데이터로 처리", value="text_only"),
        app_commands.Choice(name="엄격: 직접 처리 가능한 모델만 사용", value="strict")
    ]
)
async def ai_fallback_set(interaction: discord.Interaction, 채널: discord.TextChannel = None, 정책: str = AI_DEFAULT_FALLBACK_POLICY):
    if not can_manage_ai_settings(interaction.user):
        await interaction.response.send_message("❌ 서버 관리 권한 또는 오너 권한이 필요합니다.", ephemeral=True)
        return

    target_channel = 채널 or interaction.channel
    config = set_ai_channel_config(interaction.guild_id, target_channel.id, fallback_policy=정책)
    await interaction.response.send_message(
        f"✅ {target_channel.mention} AI 백업 정책을 `{config['fallback_policy']}`로 저장했습니다.",
        ephemeral=True
    )

@bot.tree.command(name="ai진단", description="채널 AI 모델 설정과 Ollama 연결 상태를 점검합니다.")
@app_commands.describe(채널="진단할 채널입니다. 비워두면 현재 채널을 확인합니다.")
async def ai_diagnose(interaction: discord.Interaction, 채널: discord.TextChannel = None):
    target_channel = 채널 or interaction.channel
    config = get_ai_channel_config(interaction.guild_id, target_channel.id)
    await interaction.response.defer(ephemeral=True)

    model_names = unique_ai_model_names(
        config.get("selected_profile"),
        config.get("vision_profile"),
        config.get("document_profile"),
        *normalize_ai_profile_list(config.get("fallback_profiles"))
    )
    lines = []
    for model_name in model_names:
        result = await probe_ai_model(config, model_name)
        lines.append(f"`{model_name}`: {result}")

    embed = discord.Embed(title="🩺 AI 진단", color=discord.Color.orange())
    embed.add_field(name="채널", value=target_channel.mention, inline=True)
    embed.add_field(name="모델 점검", value="\n".join(lines)[:1024] if lines else "설정된 모델이 없습니다.", inline=False)
    await interaction.followup.send(embed=embed, ephemeral=True)

# --- [수정: 개인별 맞춤 TTS 설정 명령어] ---
@bot.tree.command(name="tts설정", description="나만의 TTS 엔진, 목소리, 피치, 이름 부르기 여부를 설정합니다.")
@app_commands.describe(
    상태="TTS 기능을 켤지 끌지 선택하세요",
    엔진="사용할 TTS 엔진을 선택하세요 (기본: gTTS)",
    목소리="[Edge전용] 원하는 목소리 성별을 선택하세요",
    피치="[Edge전용] 목소리의 높낮이를 조절하세요",
    이름부르기="내 채팅을 읽을 때 닉네임을 먼저 부를지 선택하세요"
)
@app_commands.choices(
    상태=[app_commands.Choice(name="🟢 켜기", value="on"), 
         app_commands.Choice(name="🔴 끄기", value="off")],
    엔진=[app_commands.Choice(name="🤖 기본 (gTTS)", value="gtts"),
         app_commands.Choice(name="✨ 고품질 (Edge-TTS)", value="edge")],
    목소리=[app_commands.Choice(name="👩 여성 (SunHi)", value="ko-KR-SunHiNeural"),
         app_commands.Choice(name="👨 남성 (InJoon)", value="ko-KR-InJoonNeural")],
    피치=[app_commands.Choice(name="기본 톤", value="+0Hz"),
        app_commands.Choice(name="약간 높게", value="+15Hz"),
        app_commands.Choice(name="약간 낮게", value="-15Hz"),
        app_commands.Choice(name="🎈 헬륨 가스", value="+40Hz"),
        app_commands.Choice(name="🐻 동굴 소리", value="-40Hz")],
    이름부르기=[app_commands.Choice(name="O (이름 먼저 부르기)", value="yes"),
            app_commands.Choice(name="X (내용만 바로 읽기)", value="no")]
)
async def tts_setup(interaction: discord.Interaction, 상태: str, 엔진: str = "gtts", 목소리: str = "ko-KR-SunHiNeural", 피치: str = "+0Hz", 이름부르기: str = "yes"):
    data = load_tts()
    uid = str(interaction.user.id)
    
    # 선택한 옵션 저장
    data[uid] = {
        "enabled": True if 상태 == "on" else False,
        "engine": 엔진,
        "voice": 목소리,
        "pitch": 피치,
        "say_name": 이름부르기
    }
    save_tts(data)
    
    if 상태 == "on":
        engine_name = "기본 gTTS" if 엔진 == "gtts" else "고품질 Edge-TTS"
        await interaction.response.send_message(f"🎙️ **TTS 설정 완료!**\n- 엔진: {engine_name}\n- 목소리: {'여성' if 'SunHi' in 목소리 else '남성'} (Edge 전용)\n- 톤: {피치} (Edge 전용)\n- 닉네임 호출: {'사용함' if 이름부르기 == 'yes' else '사용 안 함'}", ephemeral=True)
    else:
        await interaction.response.send_message("🔇 **TTS 기능을 껐습니다.** (설정값은 안전하게 저장되었습니다)", ephemeral=True)
# -----------------------------------

def build_tts_status_embed(member, guild_id):
    data = load_tts()
    settings = data.get(str(member.id), {})
    state = get_state(guild_id)
    enabled = settings.get("enabled", False)
    engine = settings.get("engine", "gtts")
    voice = settings.get("voice", "ko-KR-SunHiNeural")
    pitch = settings.get("pitch", "+0Hz")
    say_name = settings.get("say_name", "yes")
    embed = build_embed(
        title="🎙️ TTS 상태",
        description=f"{member.mention}님의 TTS 설정입니다.",
        kind="tts" if enabled else "neutral"
    )
    embed.add_field(name="상태", value="켜짐" if enabled else "꺼짐", inline=True)
    embed.add_field(name="엔진", value="Edge-TTS" if engine == "edge" else "gTTS", inline=True)
    embed.add_field(name="이름 부르기", value="사용" if say_name == "yes" else "사용 안 함", inline=True)
    embed.add_field(name="목소리", value=f"`{voice}`", inline=False)
    embed.add_field(name="피치", value=f"`{pitch}`", inline=True)
    embed.add_field(name="TTS 볼륨", value=f"{int(state.tts_volume * 100)}%", inline=True)
    embed.add_field(name="음악 duck", value=f"{int(state.tts_duck_volume * 100)}%", inline=True)
    return embed

@bot.tree.command(name="tts상태", description="내 TTS 설정과 서버 TTS 볼륨 상태를 확인합니다.")
@app_commands.describe(대상="확인할 유저입니다. 비워두면 내 설정을 확인합니다.")
async def tts_status(interaction: discord.Interaction, 대상: discord.Member = None):
    target = 대상 or interaction.user
    if target.id != interaction.user.id and not can_manage_music_settings(interaction.user):
        await interaction.response.send_message("❌ 다른 유저 설정은 서버 관리자, DJ, 오너만 확인할 수 있습니다.", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_tts_status_embed(target, interaction.guild_id), ephemeral=True)

@bot.tree.command(name="tts테스트", description="현재 TTS 설정으로 짧은 테스트 음성을 재생합니다.")
@app_commands.describe(문장="테스트로 읽을 문장입니다. 비워두면 기본 문장을 읽습니다.")
async def tts_test(interaction: discord.Interaction, 문장: str = "푸앙봇 TTS 테스트입니다."):
    if not interaction.user.voice:
        await interaction.response.send_message("❌ 음성 채널에 먼저 들어가주세요.", ephemeral=True)
        return

    text = truncate_text(문장, 120)
    state = get_state(interaction.guild_id)

    try:
        if not interaction.guild.voice_client:
            await interaction.user.voice.channel.connect(timeout=20.0, self_deaf=True)
        elif not interaction.guild.voice_client.is_connected():
            await interaction.guild.voice_client.move_to(interaction.user.voice.channel)
    except Exception:
        await interaction.response.send_message("❌ 음성 채널 연결에 실패했어요.", ephemeral=True)
        return

    state.voice_client = interaction.guild.voice_client
    settings = load_tts().get(str(interaction.user.id), {})
    payload = {
        "text": text,
        "engine": settings.get("engine", "gtts"),
        "voice": settings.get("voice", "ko-KR-SunHiNeural"),
        "pitch": settings.get("pitch", "+0Hz")
    }
    await state.tts_queue.put(payload)
    if state.tts_task is None or state.tts_task.done():
        state.tts_task = asyncio.create_task(process_tts_queue(interaction.guild))

    await interaction.response.send_message(
        embed=build_status_embed("TTS 테스트 시작", f"`{text}`", "tts"),
        ephemeral=True
    )

@bot.tree.command(name="볼륨설정", description="기본 음악 볼륨과 TTS 중 음악 볼륨 비율을 설정합니다.")
@app_commands.describe(
    음악볼륨="평상시 음악 볼륨입니다. 0~200 사이 숫자로 입력하세요. 기본값은 50입니다.",
    tts중음악볼륨="TTS가 나오는 동안 적용할 음악 볼륨 비율입니다. 0~100 사이 숫자로 입력하세요. 기본값은 50입니다."
)
async def volume_setup(interaction: discord.Interaction, 음악볼륨: int = None, tts중음악볼륨: int = None):
    if not can_manage_music_settings(interaction.user):
        await interaction.response.send_message("❌ 서버 관리 권한, DJ 역할, 또는 오너 권한이 필요합니다.", ephemeral=True)
        return

    state = get_state(interaction.guild_id)
    changed = []

    if 음악볼륨 is not None:
        music_percent = clamp_percent(음악볼륨, 0, 200)
        state.volume = music_percent / 100
        if state.music_source is not None:
            state.music_source.volume = state.volume
        changed.append(f"기본 음악 볼륨: **{music_percent}%**")

    if tts중음악볼륨 is not None:
        duck_percent = clamp_percent(tts중음악볼륨, 0, 100)
        state.tts_duck_volume = duck_percent / 100
        changed.append(f"TTS 중 음악 볼륨 비율: **{duck_percent}%**")

    save_guild_volume_settings(interaction.guild_id, state)

    if not changed:
        changed = [
            f"기본 음악 볼륨: **{int(state.volume * 100)}%**",
            f"TTS 중 음악 볼륨 비율: **{int(state.tts_duck_volume * 100)}%**"
        ]

    await interaction.response.send_message("🎚️ **볼륨 설정**\n" + "\n".join(f"- {line}" for line in changed), ephemeral=True)

@bot.tree.command(name="업데이트", description="[개발자 전용] 깃허브에서 코드를 받아오고 봇을 재시작합니다.")
async def update_bot(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 오너(개발자)만 사용할 수 있는 명령어입니다.", ephemeral=True)
        return

    await interaction.response.send_message("🔄 **원격 업데이트를 시작합니다...**\n(서버에서 `git pull` 중...)")
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: subprocess.run(["git", "pull"], check=True, capture_output=True, text=True))
        
        await interaction.followup.send("✅ **업데이트 완료!** 봇을 재시작합니다.\n```\n" + result.stdout + "\n```")
        
        # 🌟 해결 1: 디스코드에 메시지가 완전히 전송될 수 있도록 1초 대기합니다.
        await asyncio.sleep(1)
        
        # 🌟 해결 2: 현재 실행 중인 파이썬과 파일의 절대 경로를 추적하여 강제로 완벽하게 재실행합니다.
        os.execv(sys.executable, [sys.executable, os.path.abspath(sys.argv[0])])
        
    except subprocess.CalledProcessError as e:
        await interaction.followup.send(f"❌ **Git Pull 실패:**\n```\n{e.stderr}\n```")
    except FileNotFoundError:
        await interaction.followup.send("❌ **[WinError 2] Git이 설치되어 있지 않거나 환경 변수에 없습니다!**")
    except Exception as e:
        await interaction.followup.send(f"❌ **알 수 없는 에러 발생:**\n```\n{e}\n```")

@bot.tree.command(name="입장", description="봇을 현재 음성 채널로 부릅니다.")
async def join(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect(timeout=20.0, self_deaf=True)
        state = get_state(interaction.guild_id)
        state.voice_client = interaction.guild.voice_client
        await interaction.response.send_message("🔊 **스피커 연결 완료!**")
    else:
        await interaction.response.send_message("❌ 음성 채널에 먼저 들어가주세요!", ephemeral=True)

@bot.tree.command(name="퇴장", description="봇을 내보냅니다.")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        guild_id = interaction.guild_id
        if guild_id in guild_states:
            del guild_states[guild_id] 
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 **빠이빠이!**")
    else:
        await interaction.response.send_message("❌ 들어와 있지도 않아요!", ephemeral=True)

def get_ytdl_options():
    return {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'extractor_args': {'youtube': {'player_client': ['android']}}
    }

async def extract_youtube_info(query):
    loop = bot.loop
    with youtube_dl.YoutubeDL(get_ytdl_options()) as ydl:
        return await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))

def song_from_info(info, requester):
    return Song(
        url=info['url'],
        title=info['title'],
        duration=info.get('duration'),
        thumbnail=info.get('thumbnail'),
        requester=requester
    )

async def enqueue_song_for_interaction(interaction, song, response_channel, ephemeral=False):
    state = get_state(interaction.guild_id)
    state.queue.append(song)

    if not state.current_song:
        await play_next(interaction.guild_id, response_channel)
        embed = build_embed(
            title="재생 시작",
            description=f"**{truncate_text(song.title, 180)}**",
            kind="music"
        )
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        embed.add_field(name="신청자", value=requester_label(song), inline=True)
    else:
        await update_controller_message(interaction.guild_id)
        embed = build_embed(
            title="대기열 추가됨",
            description=f"**{truncate_text(song.title, 180)}**",
            kind="success"
        )
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        embed.add_field(name="대기 순서", value=f"{len(state.queue)}번째", inline=True)
        embed.add_field(name="신청자", value=requester_label(song), inline=True)

    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

class SearchResultSelect(discord.ui.Select):
    def __init__(self, results):
        self.results = results
        options = []
        for index, info in enumerate(results[:25]):
            duration = format_time(info.get("duration"))
            uploader = info.get("uploader") or info.get("channel") or "YouTube"
            options.append(discord.SelectOption(
                label=truncate_text(info.get("title", "제목 없음"), 100),
                description=truncate_text(f"{duration} · {uploader}", 100),
                value=str(index)
            ))
        super().__init__(placeholder="재생할 검색 결과 선택", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not interaction.user.voice:
            await send_status(interaction, "음성 채널 필요", "먼저 음성 채널에 들어가 주세요.", "error", True)
            return

        index = int(self.values[0])
        info = self.results[index]
        song = song_from_info(info, interaction.user)

        for child in view.children:
            child.disabled = True
        await interaction.response.defer(ephemeral=True)
        try:
            await interaction.message.edit(view=view)
        except Exception:
            pass
        await enqueue_song_for_interaction(interaction, song, interaction.channel, ephemeral=True)

class SearchResultView(discord.ui.View):
    def __init__(self, owner_id, results):
        super().__init__(timeout=90)
        self.owner_id = owner_id
        self.add_item(SearchResultSelect(results))

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await send_status(interaction, "선택 불가", "검색을 실행한 사용자만 선택할 수 있습니다.", "error", True)
            return False
        return True

@bot.tree.command(name="재생", description="유튜브 노래를 재생합니다.")
@app_commands.describe(search="노래 제목 또는 URL")
async def play(interaction: discord.Interaction, search: str):
    is_url = search.startswith("http://") or search.startswith("https://")
    await interaction.response.defer(ephemeral=not is_url) 

    if not interaction.user.voice:
        await interaction.followup.send("❌ 음성 채널에 먼저 들어가주세요!", ephemeral=True)
        return

    state = get_state(interaction.guild_id)

    try:
        if not interaction.guild.voice_client:
            await interaction.user.voice.channel.connect(timeout=20.0, self_deaf=True)
        elif not interaction.guild.voice_client.is_connected():
            await interaction.guild.voice_client.move_to(interaction.user.voice.channel)
    except Exception as e:
        await interaction.followup.send("❌ 음성 채널 연결에 실패했어요.")
        return

    state.voice_client = interaction.guild.voice_client

    try:
        if is_url:
            info = await extract_youtube_info(search)
            if 'entries' in info:
                info = info['entries'][0]
            await enqueue_song_for_interaction(interaction, song_from_info(info, interaction.user), interaction.channel)
            return

        info = await extract_youtube_info(f"ytsearch5:{search}")
        results = [entry for entry in info.get("entries", []) if entry]
        if not results:
            await interaction.followup.send("❌ 검색 결과를 찾지 못했어요.", ephemeral=True)
            return

        embed = build_embed(
            title="검색 결과 선택",
            description=f"`{truncate_text(search, 120)}` 검색 결과에서 재생할 곡을 선택하세요.",
            kind="music"
        )
        await interaction.followup.send(embed=embed, view=SearchResultView(interaction.user.id, results[:5]), ephemeral=True)
            
    except Exception as e:
        print(f"재생 에러: {e}")
        await interaction.followup.send("❌ 노래를 찾을 수 없거나 오류가 발생했어요.", ephemeral=True)

# --- [추가: 고급 대기열 관리 명령어] ---
@bot.tree.command(name="대기열", description="현재 음악 대기열을 페이지와 선택 메뉴로 확인합니다.")
async def show_queue_command(interaction: discord.Interaction):
    state = get_state(interaction.guild_id)
    page = clamp_queue_page(state, state.queue_page)
    await interaction.response.send_message(
        embed=build_queue_embed(state, page),
        view=QueueView(interaction.guild_id, page),
        ephemeral=True
    )

@bot.tree.command(name="대기열삭제", description="대기열에서 특정 번호의 노래를 삭제합니다.")
@app_commands.describe(index="삭제할 노래의 번호 (대기열 명렁어로 확인)")
async def remove_from_queue(interaction: discord.Interaction, index: int):
    state = get_state(interaction.guild_id)
    
    if not state.queue:
        await interaction.response.send_message("❌ 대기열이 비어있습니다.", ephemeral=True)
        return
        
    if index < 1 or index > len(state.queue):
        await interaction.response.send_message(f"❌ 올바른 번호를 입력해주세요. (1 ~ {len(state.queue)} 사이)", ephemeral=True)
        return
        
    removed_song = state.queue.pop(index - 1)
    state.queue_page = clamp_queue_page(state, state.queue_page)
    await update_controller_message(interaction.guild_id)
    await interaction.response.send_message(f"🗑️ 대기열에서 **{removed_song.title}** 노래를 쏙 뺐습니다!")

@bot.tree.command(name="대기열섞기", description="현재 대기열의 노래 순서를 무작위로 셔플합니다.")
async def shuffle_queue(interaction: discord.Interaction):
    state = get_state(interaction.guild_id)
    
    if len(state.queue) < 2:
        await interaction.response.send_message("❌ 섞을 노래가 2곡 이상 필요합니다.", ephemeral=True)
        return
        
    random.shuffle(state.queue)
    state.queue_page = clamp_queue_page(state, state.queue_page)
    await update_controller_message(interaction.guild_id)
    await interaction.response.send_message("🔀 **대기열을 무작위로 섞었습니다!** `/대기열` 명령어로 바뀐 순서를 확인해보세요.")
# -----------------------------------

@bot.tree.command(name="미니푸앙", description="푸앙봇의 시그니처 텍스트 아트를 출력합니다.")
async def print_ascii_mini(interaction: discord.Interaction):
    try:
        # puang.txt 파일을 읽어옵니다. (인코딩 에러 방지를 위해 utf-8 지정)
        with open("puang.txt", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 디스코드 메시지 제한을 고려하여 안전하게 출력 (글꼴 깨짐 방지용 코드블록)
        await interaction.response.send_message(f"```{content}```")
        
    except FileNotFoundError:
        await interaction.response.send_message("❌ puang.txt 파일을 찾을 수 없습니다.")
    except Exception as e:
        await interaction.response.send_message(f"❌ 오류 발생: {e}")

@bot.tree.command(name="빅푸앙", description="푸앙봇의 빅-시그니처 텍스트 아트를 출력합니다.")
async def print_ascii_big(interaction: discord.Interaction):
    try:
        # puang-art.txt 파일을 읽어옵니다. (인코딩 에러 방지를 위해 utf-8 지정)
        with open("puang-art.txt", "r", encoding="utf-8") as f:
            content = f.read()
        
        # 디스코드 메시지 제한을 고려하여 안전하게 출력 (글꼴 깨짐 방지용 코드블록)
        await interaction.response.send_message(f"```{content}```")
        
    except FileNotFoundError:
        await interaction.response.send_message("❌ puang-art.txt 파일을 찾을 수 없습니다.")
    except Exception as e:
        await interaction.response.send_message(f"❌ 오류 발생: {e}")

@bot.tree.command(name="내정보", description="현재 나의 레벨과 경험치를 확인합니다.")
async def my_info(interaction: discord.Interaction):
    data = load_xp()
    uid = str(interaction.user.id)

    if uid not in data:
        await interaction.response.send_message("📊 아직 획득한 경험치가 없습니다. 채팅을 치거나 음악을 들어보세요!", ephemeral=True)
        return

    level = data[uid]["level"]
    xp = data[uid]["xp"]
    req_xp = get_required_xp(level)

    # 시각적인 진행률 바(Progress Bar) 계산
    progress = xp / req_xp
    bars = 15
    filled = int(progress * bars)
    bar_str = "🟩" * filled + "⬜" * (bars - filled)

    embed = discord.Embed(title=f"📈 {interaction.user.display_name}님의 프로필", color=discord.Color.blue())
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.add_field(name="현재 레벨", value=f"**Lv.{level}**", inline=True)
    embed.add_field(name="경험치 (XP)", value=f"`{xp} / {req_xp}`", inline=True)
    embed.add_field(name="다음 레벨까지", value=f"{bar_str} ({int(progress*100)}%)", inline=False)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="마크명령", description="[관리자] 마인크래프트 서버에 명령어를 전송합니다.")
@app_commands.describe(command="실행할 명령어 (예: list, stop, say Hello)")
async def mc_command(interaction: discord.Interaction, command: str):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ 관리자만 가능합니다.", ephemeral=True)
        return

    try:
        # 마크 서버(RCON)에 접속해서 명령어를 쏘고 대답을 받아옵니다.
        with MCRcon("127.0.0.1", RCON_PASSWORD, port=25575) as mcr:
            response = mcr.command(command)
            await interaction.response.send_message(f"💻 **서버 응답:**\n```\n{response}\n```")
    except Exception as e:
        await interaction.response.send_message(f"❌ 서버 연결 실패: {e}", ephemeral=True)

# 봇 실행
with open('token.txt', 'r') as f:
    TOKEN = f.read().strip()

bot.run(TOKEN)
