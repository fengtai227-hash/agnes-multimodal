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
| `model` | string | yes | `agnes-2.0-flash` |
| `messages` | array | yes | OpenAI-compatible chat messages |
| `temperature` | number | no | 0-2 |
| `top_p` | number | no | 0-1 |
| `max_tokens` | number | no | max output tokens |
| `stream` | boolean | no | enable SSE streaming |
| `tools` | array | no | Tool definitions for function calling (may be unstable) |
| `tool_choice` | string/object | no | Tool selection strategy |

### 2. Image Generation (Text-to-Image & Image-to-Image)

```
POST /v1/images/generations
```

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `model` | string | yes | `agnes-image-2.1-flash` |
| `prompt` | string | yes | English prompt recommended |
| `size` | string | no | e.g. `1024x768` |
| `extra_body` | object | no | Advanced workflow params |
| `extra_body.image` | array | no | Input image URLs for i2i |
| `extra_body.response_format` | string | no | `url` to get accessible URL |

**Pricing**: Currently FREE ($0/image)

### 3. Video Generation

```
POST /v1/videos          (create task)
GET  /v1/videos/{task_id} (query status)
```

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `model` | string | yes | `agnes-video-v2.0` |
| `prompt` | string | no | Video prompt (t2v) |
| `image` | string/array | no | Input image(s) for ti2vid/keyframes |
| `mode` | string | no | `t2v` / `ti2vid` / `keyframes` |
| `num_frames` | int | no | Must satisfy `8n+1`, max 441, default 121 |
| `frame_rate` | int | no | FPS, default 24 |

**Video Status Values**: `submitted` → `processing` → `completed` / `failed`

**Response on completion**:
```json
{
  "task_id": "xxx",
  "status": "completed",
  "video_url": "https://...mp4"
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

Non-English prompts are auto-translated via `agnes-2.0-flash` before calling image/video APIs.
Translation preserves: subject, scene, style, lighting, composition, camera movement, action descriptions.

Use `--no-translate` flag to skip translation.

---

## Video Constraints

- `num_frames` must be `8n + 1` (e.g., 9, 17, 25, 33, 41... up to 441)
- Default: `num_frames=121, frame_rate=24` (~5 seconds)
- Quick test: `num_frames=81` (~3.4 seconds)
- Max wait for polling: 600s (10 min), check interval: 5s
