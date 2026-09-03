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
| `model` | string | yes | `agnes-2.5-flash` |
| `messages` | array | yes | OpenAI-compatible chat messages |
| `temperature` | number | no | 0-2 |
| `top_p` | number | no | 0-1 |
| `max_tokens` | number | no | max output tokens (2.5 supports up to 65.5K) |
| `stream` | boolean | no | enable SSE streaming |
| `tools` | array | no | Tool definitions for function calling |
| `tool_choice` | string/object | no | Tool selection strategy |
| `chat_template_kwargs` | object | no | `{"enable_thinking": true}` to enable 2.5 Thinking mode |

**2.5 Flash Specs**: context 512K · max output 65.5K · also supports Responses API (`/v1/responses`) and Anthropic Messages API (`/v1/messages`) · pricing FREE ($0/1M tokens)

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
| `extra_body.image` | array | no | Input image URLs for i2i |
| `extra_body.response_format` | string | no | `url` to get accessible URL |

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

### 3. Video Generation — Engine 1 (V2.0)

```
POST /v1/videos          (create task)
GET  /agnesapi?video_id={id}  (query status, text/i2v tasks)
GET  /v1/videos/{task_id} (fallback)
```

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `model` | string | yes | `agnes-video-v2.0` |
| `prompt` | string | no | Video prompt (t2v) |
| `image` | string/array | no | Input image(s) for ti2vid/keyframes |
| `mode` | string | no | `t2v` / `ti2vid` / `keyframes` |
| `num_frames` | int | no | Must satisfy `8n+1`, max 441, default 121 |
| `frame_rate` | int | no | FPS, default 24 |

**Pricing**: FREE ($0/second)

### 4. Video Generation — Engine 2 (Video 2.5 / 2.5 Flash)

```
POST /v1/videos   (create task)
GET  /agnesapi?video_id={id}&model_name={model}  (query status — model_name REQUIRED for keyframe/reference)
```

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `model` | string | yes | `agnes-video-2.5-flash` (default) or `agnes-video-2.5` (paid) |
| `prompt` | string | no | Video prompt; reference mode uses `<Picture N>` / `<Audio N>` placeholders |
| `mode` | string | yes | `text` / `keyframe` / `reference` |
| `seconds` | string | no | `"4"`–`"12"` (string), default `"5"` |
| `size` | string | no | flash: only `"720P"`; paid: `"720P"`/`"960P"`/`"2K"` |
| `aspect_ratio` | string | no | `16:9`(default)/`9:16`/`1:1`/`4:3`/`3:4`/`21:9` |
| `seed` | int | no | Reproducible results |
| `first_frame` | string | keyframe | First frame URL (with `last_frame`, at least one required) |
| `last_frame` | string | keyframe | Last frame URL |
| `images` | string[] | reference | Reference image URLs (flash max 5) |
| `audios` | string[] | reference | Reference audio URLs (flash max 3) |
| `videos` | object[] | reference | Reference videos (flash NOT supported; paid only) |

**Mode rules**: `text` forbids all media fields; `keyframe` requires first/last frame and forbids images/audios/videos;
`reference` requires images/audios/videos and forbids first/last frame.
**Pricing**: `agnes-video-2.5-flash` limited-time FREE ($0/second, 720P only);
`agnes-video-2.5`: 720P $0.025/s, 960P $0.040/s, 2K $0.055/s (input images: first 5 free, then $0.005/img).
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

## Video Constraints

### Engine 1 (V2.0)
- `num_frames` must be `8n + 1` (e.g., 9, 17, 25, 33, 41... up to 441)
- Default: `num_frames=121, frame_rate=24` (~5 seconds)
- Quick test: `num_frames=81` (~3.4 seconds)
- Max wait for polling: 600s (10 min), check interval: 5s

### Engine 2 (Video 2.5 / 2.5 Flash)
- `seconds` string `"4"`–`"12"`, default `"5"`; `n` fixed to 1
- flash: `size` must be `"720P"`; images ≤ 5; audios ≤ 3; videos unsupported (400 errors otherwise)
- Query must carry `model_name=agnes-video-2.5-flash` for keyframe/reference tasks
- Unsupported in 2.5 API: `width`/`height`/`fps`/`num_frames`/`num_inference_steps`/`quality` (return 400)
