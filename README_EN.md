# Agnes Multimodal — Full-Stack AI Generation Skill for WorkBuddy

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-WorkBuddy-orange)](https://www.codebuddy.cn/)

A **WorkBuddy-native Skill** wrapping all [Agnes AI (Sapiens AI)](https://agnes-ai.com/) generation APIs. One script for text, image, video, and vision — with auto Chinese-to-English translation and zero external dependencies.

---

## Capabilities

| Capability | Model | Status |
|------|------|:--:|
| 📝 Text Generation | `agnes-2.5-flash` | ✅ |
| 🧠 Thinking / Reasoning | `agnes-2.5-flash` | ✅ |
| 🖼️ Text-to-Image | `agnes-image-2.5-flash` (fallback 2.1 via --model) | ✅ |
| 🔄 Image-to-Image | `agnes-image-2.5-flash` (auto-ratio) | ✅ |
| 👁️ Image Recognition (Vision) | `agnes-2.5-flash` | ✅ |
| 🎬 Text-to-Video | `agnes-video-v2.0` / `agnes-video-2.5-flash` | ✅ |
| 🎞️ Image-to-Video | `agnes-video-v2.0` (ti2vid) / `video25 --image-url` | ✅ |
| 🔗 Keyframe / First-Last-Frame | `agnes-video-v2.0` / `video25 --first/last-frame` | ✅ |
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

# Text-to-image (tier sizes + ratio supported)
python scripts/agnes_client.py image "A futuristic city at sunset, cinematic" --size 2K --ratio 16:9
python scripts/agnes_client.py image "Cinematic hero image" --size 2K --ratio 16:9

# Image-to-image
python scripts/agnes_client.py image "Transform to cyberpunk night" --image-url "https://example.com/input.png"

# Vision / Image understanding
python scripts/agnes_client.py vision --image-url "https://example.com/photo.png"
python scripts/agnes_client.py vision --image-url URL --prompt "What brand is this watch?"

# Text-to-video
python scripts/agnes_client.py video "A drone flying over mountains at sunrise" --poll

# Image-to-video
python scripts/agnes_client.py video "Add gentle motion to this scene" --image-url "https://example.com/frame.png" --poll

# Keyframe animation
python scripts/agnes_client.py video --keyframes "https://a.com/1.png,https://a.com/2.png,https://a.com/3.png" --poll

# Submit only (no polling)
python scripts/agnes_client.py video "..." --no-poll

# Query video status
python scripts/agnes_client.py video-status TASK_ID

# Translate Chinese → English
python scripts/agnes_client.py translate "一只在月光下散步的猫"
```

---

## Key Features

### 👁️ Vision Bridge

`agnes-2.5-flash` supports OpenAI Vision API format. Use the `vision` command to generate text descriptions of images, then feed them to any text-only model:

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
| `num_frames` | **Must** satisfy `8n + 1`, max 441 |
| Default | `--num-frames 121` (~5s @ 24fps) |
| Quick test | `--num-frames 81` (~3.4s) |
| Poll timeout | 600s |

---

## Pricing

| Model | Pricing |
|------|------|
| `agnes-2.5-flash` (Text/Vision) | Free |
| `agnes-image-2.5-flash` / `agnes-image-2.1-flash` (Image) | **Free** |
| `agnes-video-v2.0` (Video V2.0) | **Free** |
| `agnes-video-2.5-flash` (Next-gen video) | **Limited-time free** (720P) |

---

## Known Limitations

- Tool Calling may be unstable
- Video generation occasionally returns `division by zero` server errors
- Image API only accepts HTTP(S) URLs as input (no base64)
- Multi-image / keyframe video not fully end-to-end verified

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
