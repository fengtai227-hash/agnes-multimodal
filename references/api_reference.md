# Agnes AI API Reference

## Base Info

- **Base URL**: `https://apihub.agnes-ai.com`
- **Auth**: `Authorization: Bearer YOUR_API_KEY`
- **Content-Type**: `application/json`

---

## Endpoints

### 1. Text Generation

```
POST /v1/chat/completions
```

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `model` | string | yes | `agnes-2.5-flash` (default) or `agnes-3.0-flash` (512K context) |
| `messages` | array | yes | OpenAI-compatible chat messages |
| `temperature` | number | no | 0-2 |
| `top_p` | number | no | 0-1 |
| `max_tokens` | number | no | max output tokens (2.5 supports up to 65.5K) |
| `stream` | boolean | no | enable SSE streaming |
| `tools` | array | no | Tool definitions for function calling |
| `tool_choice` | string/object | no | Tool selection strategy |
| `chat_template_kwargs` | object | no | `{"enable_thinking": true}` to enable 2.5 Thinking mode |

**2.5 Flash Specs**: context 512K · max output 65.5K · also supports Responses API (`/v1/responses`) and Anthropic Messages API (`/v1/messages`) · pricing FREE ($0/1M tokens)

**3.0 Flash Specs** (optional, `--model agnes-3.0-flash`): context 512K · max output 65,536 · pricing FREE ($0/1M tokens) · vision input verified working and markedly faster / less timeout-prone than 2.5-flash

### 2. Image Generation (Text-to-Image & Image-to-Image)

```
POST /v1/images/generations
```

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `model` | string | yes | `agnes-image-2.5-flash` (latest, default) or `agnes-image-2.1-flash` (legacy) |
| `prompt` | string | yes | English prompt recommended |
| `size` | string | no | tier (`1K`/`2K`/`3K`/`4K`, recommended) or exact (`1024x768`, may be standardized) |
| `ratio` | string | no | aspect ratio: `1:1`/`3:4`/`4:3`/`16:9`/`9:16`/`2:3`/`3:2`/`21:9` (use with tier size) |
| `extra_body` | object | no | Advanced workflow params |
| `extra_body.image` | array | no | Input images for i2i: public URLs **or Data URI base64** (`data:image/png;base64,...`) — official docs confirm both |
| `extra_body.response_format` | string | no | `url` or `b64_json` (output format) |
| `return_base64` | boolean | no | top-level; true → output as base64 (t2i) |

**Pricing**: Currently FREE ($0/image) for both 2.1 & 2.5 flash, all resolution tiers.
**Note**: `response_format` must NOT be placed at payload top level. Do NOT pass `tags: ["img2img"]`.
**Output size reference (tier × ratio)**:
| Ratio | 1K | 2K | 3K | 4K |
|-------|----|----|----|----|
| `1:1` | 1024x1024 | 2048x2048 | 3072x3072 | 4096x4096 |
| `16:9` | 1312x736 | 2624x1472 | 3936x2208 | 5248x2944 |
| `9:16` | 736x1312 | 1472x2624 | 2208x3936 | 2944x5248 |
| `3:4` | 864x1152 | 1728x2304 | 2592x3456 | 3456x4608 |
| `4:3` | 1152x864 | 2304x1728 | 3456x2592 | 4608x3456 |
| `2:3` | 832x1248 | 1664x2496 | 2496x3744 | 3328x4992 |
| `3:2` | 1248x832 | 2496x1664 | 3744x2496 | 4992x3328 |
| `21:9` | 1568x672 | 3136x1344 | 4704x2016 | 6272x2688 |

### 3. Video Generation (Video 2.5 Flash)

> **Removed**: the former "Engine 1" (`agnes-video-v2.0`) was officially retired on 2026-09-25 23:59:59 (UTC+8). This skill no longer exposes its endpoint, params or sub-command.

```
POST /v1/videos   (create task)
GET  /agnesapi?video_id={id}&model_name={model}  (query status — model_name REQUIRED for keyframe/reference)
```

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `model` | string | yes | `agnes-video-2.5-flash` (default, FREE) or `agnes-video-2.5` (paid — CLI blocks it unless `--allow-paid`) |
| `prompt` | string | no | Video prompt; reference mode uses `<Picture N>` / `<Audio N>` placeholders |
| `mode` | string | yes | `text` / `keyframe` / `reference` |
| `seconds` | string | no | `"4"`–`"12"` (string), default `"5"` |
| `size` | string | no | flash: only `"720P"`; paid: `"720P"`/`"1080P"`/`"1K"`/`"2K"` (old `960P` retired) |
| `aspect_ratio` | string | no | `16:9`(default)/`9:16`/`1:1`/`4:3`/`3:4`/`21:9` |
| `seed` | int | no | Reproducible results |
| `first_frame` | string | keyframe | First frame: public URL per official docs (local file → base64 works per community plugins, undocumented; fallback to URL). With `last_frame`, at least one required |
| `last_frame` | string | keyframe | Last frame: same URL/base64 note as first_frame |
| `images` | string[] | reference | Reference images (flash max 5). Official docs: public URLs; base64 undocumented |
| `audios` | string[] | reference | Reference audio URLs (flash max 3) |
| `videos` | object[] | reference | Reference videos (flash NOT supported; paid only) |

**Mode rules**: `text` forbids all media fields; `keyframe` requires first/last frame and forbids images/audios/videos;
`reference` requires images/audios/videos and forbids first/last frame.
**Pricing**: `agnes-video-2.5-flash` limited-time FREE ($0/second, 720P only) — the skill default;
`agnes-video-2.5` (paid; CLI refuses it without `--allow-paid`): 720P $0.025/s, 1080P/1K $0.040/s, 2K $0.055/s (input images: first 5 free, then $0.005/img).
**Aspect output (720P)**: 21:9=1680x720, 16:9≈1280x704, 4:3=960x720, 1:1=720x720, 3:4=720x960, 9:16=720x1280.

**Video Status Values**: `queued` → `in_progress` → `completed` / `failed`

**Response on completion**:
```json
{
  "id": "task_xxx",
  "video_id": "task_xxx",
  "status": "completed",
  "progress": 100,
  "metadata": { "url": "https://...mp4" }
}
```

---

## Prompt Engineering Best Practices

### Image Prompt Structure
```
[Subject] + [Scene/Environment] + [Style] + [Lighting] + [Composition] + [Quality Requirements]
```

Example:
> A luminous floating city above a misty canyon at sunrise, cinematic realism, wide-angle composition, rich architectural details, soft golden light, high visual density

### Image-to-Image Prompt
Must describe both what to change AND what to preserve:
> Transform the scene into a rain-soaked cyberpunk night with neon reflections while preserving the original composition and main subject layout.

### Video Prompt
Include camera movement and temporal elements:
> A drone slowly ascending over a mountain range, gentle forward movement, golden hour lighting, smooth cinematic pan

---

## Auto-Translation

Non-English prompts are auto-translated via `agnes-2.5-flash` before calling image/video APIs.
Translation preserves: subject, scene, style, lighting, composition, camera movement, action descriptions.

Use `--no-translate` flag to skip translation.

---

## Video Constraints (Video 2.5 Flash)

- `seconds` string `"4"`–`"12"`, default `"5"`; `n` fixed to 1
- flash: `size` must be `"720P"`; images ≤ 5; audios ≤ 3; videos unsupported (400 errors otherwise)
- Query must carry `model_name=agnes-video-2.5-flash` for keyframe/reference tasks
- Unsupported in 2.5 API: `width`/`height`/`fps`/`num_frames`/`num_inference_steps`/`quality` (return 400)
- Max wait for polling: 600s (10 min), check interval: 5s
- Paid model `agnes-video-2.5` additionally requires `--allow-paid`; available sizes `720P`/`1080P`/`1K`/`2K`
