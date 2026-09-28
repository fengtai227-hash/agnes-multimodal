# Agnes Multimodal — Full-Stack AI Generation Skill for WorkBuddy

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-WorkBuddy-orange)](https://www.codebuddy.cn/)

A **WorkBuddy-native Skill** wrapping all [Agnes AI (Sapiens AI)](https://agnes-ai.com/) generation APIs. One script for text, image, video, and vision — with auto Chinese-to-English translation and zero external dependencies.

---

## Capabilities

| Capability | Model | Status |
|------|------|:--:|
| 📝 Text Generation | `agnes-2.5-flash` (optional `agnes-3.0-flash`) | ✅ |
| 🧠 Thinking / Reasoning | `agnes-2.5-flash` | ✅ |
| 🖼️ Text-to-Image | `agnes-image-2.5-flash` (fallback 2.1 via --model) | ✅ |
| 🔄 Image-to-Image | `agnes-image-2.5-flash` (auto-ratio) | ✅ |
| 👁️ Image Recognition (Vision) | `agnes-2.5-flash` / `agnes-3.0-flash` | ✅ |
| 🎬 Text-to-Video | `agnes-video-2.5-flash` (text, free 720P) | ✅ |
| 🎞️ Image-to-Video / Reference | `video25 --image-url` | ✅ |
| 🔗 Keyframe / First-Last-Frame | `video25 --first/last-frame` | ✅ |
| 🌐 Auto Translation (CN→EN) | `agnes-2.5-flash` | ✅ |
| ⏳ Async Polling | — | ✅ |

---

## Installation

### Option 1: WorkBuddy Skill Marketplace (Recommended)

Search for "agnes-multimodal" in the WorkBuddy Skill marketplace, or import the `.skill` file directly.

### Option 2: Manual Install

```bash
git clone https://github.com/YOUR_USERNAME/agnes-multimodal.git \
  ~/.workbuddy/skills/agnes-multimodal
```

### Configure API Key

Edit `~/.workbuddy/skills/agnes-multimodal/scripts/agnes_client.py`:

```python
API_KEY = "YOUR_AGNES_API_KEY_HERE"  # Replace with your API Key
```

Or set via environment variable (automatic fallback):

```bash
export AGNES_API_KEY="your_api_key"
```

> Supported env vars: `AGNES_API_KEY` / `AGNES_API_TOKEN` / `APIHUB_AGNES_API_KEY`

---

## Quick Start

```bash
cd ~/.workbuddy/skills/agnes-multimodal
python scripts/agnes_client.py smoke-test
```

---

## CLI Reference

```bash
# Text generation
python scripts/agnes_client.py text "Explain quantum computing" --stream
python scripts/agnes_client.py text "Debug this code" --thinking  # 2.5 thinking mode
python scripts/agnes_client.py text "Hard reasoning task" --model agnes-3.0-flash  # optional 3.0 (512K ctx)

# Text-to-image (tier sizes + ratio supported)
python scripts/agnes_client.py image "A futuristic city at sunset, cinematic" --size 2K --ratio 16:9
python scripts/agnes_client.py image "Cinematic hero image" --size 2K --ratio 16:9

# Image-to-image
python scripts/agnes_client.py image "Transform to cyberpunk night" --image-url "https://example.com/input.png"

# Vision / Image understanding
python scripts/agnes_client.py vision --image-url "https://example.com/photo.png"
python scripts/agnes_client.py vision --image-url URL --prompt "What brand is this watch?"
python scripts/agnes_client.py vision --image-url "D:\\pics\\watch.png" --model agnes-3.0-flash  # faster

# Text-to-video (default free engine: Video 2.5 Flash, 720P)
python scripts/agnes_client.py video25 "A drone flying over mountains at sunrise" --poll

# Reference generation (use <Picture N> placeholders)
python scripts/agnes_client.py video25 "The character in <Picture 1> runs in a flower field" --image-url "https://example.com/char.png" --poll

# First/last frame control
python scripts/agnes_client.py video25 "The character turns and walks to the window" --first-frame "https://a.com/f.png" --last-frame "https://a.com/l.png" --poll

# Submit only (no polling)
python scripts/agnes_client.py video25 "..." --no-poll

# Query video status (keyframe/reference tasks require --model)
python scripts/agnes_client.py video-status TASK_ID --model agnes-video-2.5-flash

# Translate Chinese → English
python scripts/agnes_client.py translate "一只在月光下散步的猫"
```

---

## Key Features

### 👁️ Vision Bridge

`agnes-2.5-flash` / `agnes-3.0-flash` support OpenAI Vision API format. Use the `vision` command to generate text descriptions of images, then feed them to any text-only model (3.0-flash is faster and far less prone to timeouts):

```
Image → vision command → text description → any LLM for further analysis
```

### 🌐 Auto Translation

Chinese prompts are automatically translated to English via `agnes-2.5-flash`, preserving subject, scene, style, and lighting. Use `--no-translate` to skip.

### ⚡ Zero Dependencies

Pure Python standard library (`urllib` + `json` + `argparse`). No `pip install` needed.

---

## Video Constraints

| Parameter | Constraint |
|------|------|
| Engine | `agnes-video-2.5-flash` (default, free, 720P only) |
| `seconds` | string `"4"`–`"12"`, default `"5"` |
| `size` | fixed `720P` for flash; paid `agnes-video-2.5` supports `720P`/`1080P`/`1K`/`2K` |
| `aspect_ratio` | `21:9` / `16:9`(default) / `4:3` / `1:1` / `3:4` / `9:16` |
| Flash limits | ≤5 reference images, ≤3 audios, no video reference |
| Poll timeout | 600s |

---

## Pricing

| Model | Pricing |
|------|------|
| `agnes-2.5-flash` (Text/Vision, default) | Free |
| `agnes-3.0-flash` (Text/Vision, optional) | Free (512K context) |
| `agnes-image-2.5-flash` / `agnes-image-2.1-flash` (Image) | **Free** |
| `agnes-video-2.5-flash` (Video, **default**) | **Limited-time free** (720P only) |
| `agnes-video-2.5` (Video, paid, requires `--allow-paid`) | $0.025/s (720P) / $0.040/s (1080P, 1K) / $0.055/s (2K) |

---

## Known Limitations

- Tool Calling may be unstable
- Video generation occasionally returns `division by zero` server errors
- Image API accepts **both public URLs and base64 Data URIs** as input (official docs: "Supports public URLs or Data URI Base64"); the CLI auto-converts local file paths to Data URIs — no image host needed
- Video media fields (first_frame/last_frame/images) are only documented for public URLs; local-path base64 is undocumented behavior — fall back to a public URL if it fails
- `agnes-video-v2.0` was officially retired on 2026-09-25; this skill removed its entry point entirely
- The paid video model `agnes-video-2.5` is blocked by default and requires an explicit `--allow-paid`

---

## Differences from Original

This project is inspired by [Yacey/agnes-ai-generation-skill](https://github.com/Yacey/agnes-ai-generation-skill), with the following improvements for WorkBuddy:

| Dimension | Original | agnes-multimodal |
|------|---------|-----------------|
| Target Platform | Generic Agent (Codex/Claude/OpenClaw) | **WorkBuddy** |
| Vision Support | ❌ | ✅ New |
| Standalone Translate | ❌ | ✅ New |
| Video Mode Fix | — | ✅ `i2v` → `ti2vid` |
| Dependencies | — | ✅ Zero (pure stdlib) |

---

## Acknowledgments

- [Yacey/agnes-ai-generation-skill](https://github.com/Yacey/agnes-ai-generation-skill) — Original Skill implementation providing API structure and design reference
- [Agnes AI / Sapiens AI](https://agnes-ai.com/) — Underlying models and API provider

---

## License

MIT License — see [LICENSE](LICENSE)
