---
name: agnes-multimodal
description: >
  Agnes AI 全模态生成技能。覆盖文本生成(agnes-2.5-flash / agnes-3.0-flash)、文生图/图生图(agnes-image-2.5-flash 最新一代)、
  视频生成(agnes-video-2.5-flash，限时免费 720P，text/keyframe/reference 三模式)、
  自动中译英、异步轮询。一个 Skill 全部搞定。 当用户需要 AI 生成文本、图片、视频，或提到
  "Agnes"、"agnes"、"AI 画图"、"AI 生成视频"、 "AI 图片"、"文生图"、"图生图"、"文生视频"、
  "图生视频"、"关键帧动画"、"首尾帧"、"用 Agnes 生成" 时触发。
  API Key 默认从环境变量 AGNES_API_KEY 读取，也可在 agnes_client.py 中硬编码。
---

# Agnes AI 全模态生成 Skill

## 概述

本 Skill 封装了 Agnes AI (Sapiens AI) 的全部生成能力，通过一个 CLI 脚本统一调用：

- **文本生成**: `agnes-2.5-flash`（默认，支持 Thinking 推理模式，$0）；可选 `agnes-3.0-flash`（512K 上下文，输出上限 65,536，$0）
- **图片理解/Vision**: `agnes-2.5-flash` / `agnes-3.0-flash`（OpenAI Vision API 兼容；3.0 更快，实测更不易超时）
- **文生图/图生图**: `agnes-image-2.5-flash`（最新一代，高信息密度优化；可用 `--model agnes-image-2.1-flash` 回退上一代）
- **视频生成**: `agnes-video-2.5-flash` — **唯一默认引擎**，限时免费 $0/秒（仅 720P），text/keyframe/reference 三模式，支持图片/音频参考
- **自动翻译**: 中文提示词自动译英文后调用 API
- **异步轮询**: 视频任务自动轮询直到完成

> ⚠️ **付费模型默认禁用**：`agnes-video-2.5`（$0.025/秒起，**无优惠**）必须显式追加 `--allow-paid` 才会调用，避免误产生费用。
> 旧的 `agnes-video-v2.0` 引擎已于 2026-09-25 官方下线，本 skill 已彻底移除其入口。

## 前置条件

1. 确认 API Key 已配置：
   - 优先读取 `scripts/agnes_client.py` 中硬编码的 `API_KEY`
   - 如为占位符 `YOUR_AGNES_API_KEY_HERE`，则回退读取环境变量 `AGNES_API_KEY`
   - 若均未配置，提醒用户在代码或环境变量中设置 API Key

2. Python 3.8+，标准库 `urllib` + `json` 即可，无需额外依赖。

## CLI 命令速查

脚本位置: `scripts/agnes_client.py`

```
# 文本生成
python scripts/agnes_client.py text "你的提示词"
python scripts/agnes_client.py text "你好" --stream
python scripts/agnes_client.py text "帮我写一个快速排序" --thinking  # 2.5 推理模式
python scripts/agnes_client.py text "复杂推理题" --model agnes-3.0-flash   # 可选 3.0（512K 上下文）

# 文生图（agnes-image-2.5-flash，默认 1K；推荐档位 size + ratio）
python scripts/agnes_client.py image "A futuristic city at sunset, cinematic realism" --size 2K --ratio 16:9
python scripts/agnes_client.py image "一只在月光下散步的猫"
python scripts/agnes_client.py image "..." --model agnes-image-2.1-flash   # 回退上一代

# 图生图（自动比例检测 — 默认按主参考图比例输出；输入支持 URL 或本地文件路径）
python scripts/agnes_client.py image "Transform to cyberpunk night" --image-url "https://...input.png" --image-url "https://...ref.png"
python scripts/agnes_client.py image "Transform to cyberpunk night" --image-url "D:\\pics\\model.png"   # 本地路径自动转 base64 Data URI（官网明确支持）

# 图生图 + 手动指定 ratio（不自动检测）
python scripts/agnes_client.py image "Transform to cyberpunk night" --image-url "https://...input.png" --ratio 16:9

# ── 视频生成：Video 2.5 Flash（限时免费，仅 720P）──
python scripts/agnes_client.py video25 "雨后的未来城市街道，霓虹灯倒影，电影级运镜" --poll          # text 文生视频
python scripts/agnes_client.py video25 "人物自然转身走向窗边" --first-frame "https://.../f.png" --last-frame "https://.../l.png" --poll  # keyframe 首尾帧
python scripts/agnes_client.py video25 "以 <Picture 1> 为角色参考在花田奔跑" --image-url "https://.../char.png" --poll  # reference 图片参考
python scripts/agnes_client.py video25 "跟随 <Audio 1> 节奏生成夜景" --audio-url "https://.../music.mp3" --poll  # reference 音频参考
python scripts/agnes_client.py video25 "..." --model agnes-video-2.5 --allow-paid --size 1080P  # 付费，需 --allow-paid 确认（$0.040/秒）

# 只提交视频任务不等待
python scripts/agnes_client.py video25 "..." --no-poll

# 查询视频任务状态（2.5 的 keyframe/reference 任务必须带 --model）
python scripts/agnes_client.py video-status TASK_ID
python scripts/agnes_client.py video-status TASK_ID --model agnes-video-2.5-flash

# 翻译中文提示词
python scripts/agnes_client.py translate "一只猫"

# 图片理解 / Vision（默认 agnes-2.5-flash，可换更快的 agnes-3.0-flash）
python scripts/agnes_client.py vision --image-url "https://example.com/photo.png"
python scripts/agnes_client.py vision --image-url "https://example.com/photo.png" --prompt "What brand is this watch?"
python scripts/agnes_client.py vision --image-url "D:\\pics\\watch.png" --model agnes-3.0-flash

# 冒烟测试（验证 API 连通性）
python scripts/agnes_client.py smoke-test
```

## 完整工作流

### 文生图流程

1. 接收用户的中文/英文提示词
2. 若含中文且未指定 `--no-translate`，自动调用 `agnes-2.5-flash` 翻译为英文
3. 调用 `POST /v1/images/generations`（模型默认: `agnes-image-2.5-flash`）
4. 从响应 `data[0].url` 提取图片 URL
5. 将结果返回给用户（显示 URL，或尝试用 `curl`/浏览器打开）

> 尺寸建议：文生图推荐 `--size 2K --ratio 16:9` 这类"档位 + 比例"写法以获得可预期尺寸；
> 不支持的精确尺寸（如 1920x1080）会被服务端标准化，需自行裁剪。

### 图生图流程

1. 确认用户提供了输入图片 URL、Data URI 或本地路径（本地路径会自动转为 base64 Data URI）
2. 如需翻译提示词，执行翻译
3. 调用同一 endpoint，在 `extra_body.image` 中传入输入图片数组（URL 或 `data:image/png;base64,...`）
4. 返回生成结果

### 视频生成流程（引擎选择）

视频生成统一走 `video25` 子命令：

| 模型 | `--model` | 特点 | 价格 |
|---|---|---|---|
| **Video 2.5 Flash**（默认） | `agnes-video-2.5-flash` | text/keyframe/reference 三模式，参考图(≤5)/音频(≤3)，镜头可控 | **限时免费 $0/秒**（仅 720P） |
| Video 2.5（付费） | `agnes-video-2.5` + `--allow-paid` | 同上，另支持 1080P/1K/2K 与视频参考 | $0.025~$0.055/秒，**无优惠** |

**Video 2.5 Flash（`video25`）工作流：**

1. 按素材自动推断模式（`--mode auto`），也可显式指定：
   - `text`：纯文本 → 无任何媒体参数
   - `keyframe`：`--first-frame` / `--last-frame`（至少一个）约束起止构图
   - `reference`：`--image-url`（≤5 张）/ `--audio-url`（≤3 段）；提示词用 `<Picture N>` / `<Audio N>` 占位符指代素材
2. 提交 `POST /v1/videos`，参数：`mode` + `seconds`("4"~"12") + `size`(flash 仅 720P) + `aspect_ratio` + `seed`
3. 轮询 `GET /agnesapi?video_id=<ID>&model_name=agnes-video-2.5-flash`（keyframe/reference 必须带 model_name）
4. 状态 `completed` 后从响应提取视频 URL

> ⚠️ `video25` 使用 2.5 参数体系（seconds/mode/aspect_ratio/size），不接受 num_frames/width/height/fps/negative_prompt 等旧 V2.0 参数（会返回 400）。

### 视频参数约束（Video 2.5）

- `seconds` 为字符串 `"4"`~`"12"`，默认 `"5"`
- `size`：flash 固定 `720P`（唯一免费档位）；付费模型 `agnes-video-2.5` 可选 `720P`/`1080P`/`1K`/`2K`（旧 `960P` 已废弃）
- `aspect_ratio`：`21:9` / `16:9`(默认) / `4:3` / `1:1` / `3:4` / `9:16`
- flash 限制：参考图片 ≤5 张、音频 ≤3 段、**不支持视频参考**（付费版支持 `videos`）
- 实测 720P 16:9 输出约 1280x704

### 图片理解 (Vision) 流程

`agnes-2.5-flash` / `agnes-3.0-flash` 支持 OpenAI Vision API 格式的多模态输入，可分析图片内容并返回文字描述。这是"给不具备视觉能力的模型提供眼睛"的桥接方案。**3.0-flash 实测图像输入更快、更不易超时**（2.5-flash 的 vision 端点此前多次超时），可用 `--model agnes-3.0-flash` 切换。

1. 图片可为公网 HTTP(S) URL 或本地路径（本地路径自动转 base64 Data URI，OpenAI Vision 兼容层支持）
2. 调用 `vision` 命令，传入图片 + 可选的分析提示词
3. 返回文字描述，可直接作为上下文传给其他模型（如"请对这张图片中的手表设计给出改进建议"——先 vision 获取描述，再传给任意文本模型分析）

Vision 命令参数：
- `--image-url`（必填，可多次指定）: 要分析的图片 URL
- `--prompt`（可选）: 分析提示词，默认 "Describe this image in detail."
- `--system`（可选）: 系统提示词
- `--max-tokens`（可选）: 最大输出 tokens，默认 1000
- `--model`（可选）: 视觉模型，默认 `agnes-2.5-flash`；可换 `agnes-3.0-flash`（更快）
- `--no-translate`（可选）: 跳过自动翻译（英文 prompt 建议使用）

## 提示词最佳实践

### 图片 Prompt 结构

```
[Subject] + [Scene] + [Style] + [Lighting] + [Composition] + [Quality]
```

示例:
> A luxury watch with a black leather strap on a marble surface, soft studio lighting, macro photography, 8K detail, high visual density

### 图生图 Prompt

明确描述要改变什么 + 保持什么:
> Transform the background to a dark luxury setting while preserving the watch design and angle.

### 视频 Prompt

加入运镜和时间元素:
> A slow 360-degree rotation around the watch, revealing every detail, cinematic lighting, smooth movement

## 价格

| 模型 | 定价 |
|------|------|
| `agnes-2.5-flash` (文本/Vision/推理，默认) | **免费** ($0/1M tokens) |
| `agnes-3.0-flash` (文本/Vision，可选) | **免费** ($0/1M tokens，512K 上下文) |
| `agnes-image-2.5-flash` (图片，最新一代) | **免费** ($0/图，所有 1K~4K 档位) |
| `agnes-image-2.1-flash` (图片，上一代) | **免费** ($0/图) |
| `agnes-video-2.5-flash` (视频，**默认**) | **限时免费** ($0/秒, 仅 720P) |
| `agnes-video-2.5` (视频，付费，需 `--allow-paid`) | $0.025/秒(720P) / $0.040/秒(1080P、1K) / $0.055/秒(2K) |

> 价格以官网 https://www.agnes-ai.com/zh-Hans/docs/pricing 为准，免费政策可能随平台公告调整。

## 已知限制

- 2.5 Thinking 模式会返回 `reasoning_content` 字段（思考过程），会增加少量输出 token
- 视频生成偶有 `division by zero` 服务端错误
- `agnes-video-v2.0` 已于 2026-09-25 官方下线，本 skill 已彻底移除其入口（API 侧虽仍能出片，但无文档承诺，不应再使用）
- 图像 API（`/v1/images/generations`）输入**同时支持公网 URL 和 base64 Data URI**（官网文档明确：`image` 数组 "Supports public URLs or Data URI Base64"，本地文件无需再传图床）；输出可选 URL 或 Base64（`return_base64: true` 或 `extra_body.response_format: b64_json`）
- 视频媒体字段（first_frame/last_frame/images/audios/videos）官网文档仅写公网 URL，且要求 "must be publicly accessible"；脚本对视频帧也支持本地路径转 base64，但属**未文档化行为**（社区 ComfyUI 插件实测可用），失败时请回退公网 URL
- 视频输入**不支持**传视频文件 base64（videos 字段仅接受带 url 的对象，且 flash 版不支持视频参考）
- `agnes-video-2.5-flash` 仅 720P，不支持视频参考；确需 1080P/1K/2K 或视频参考时，用付费 `--model agnes-video-2.5 --allow-paid`
- `video25` 的 keyframe/reference 任务查询必须带 `--model agnes-video-2.5-flash`

## 图生图（i2i）输入格式（2026-09-11 官网查证）

- `extra_body.image` 数组元素可为：`https://...` 公网 URL **或** `data:image/png;base64,...` Data URI（官网 agnes-image-2.0/2.1-flash 文档原文："Supports public URLs or Data URI Base64"）
- 本技能的 `--image-url` 参数同时接受 URL 和本地文件路径，本地路径自动转 Data URI（含 jpg/png/webp/gif/bmp）
- 自动比例检测对三种输入形态均有效（Data URI/本地路径直接解码文件头，无需下载）

## 自动比例检测（i2i）

i2i 时若未指定 `--ratio`，脚本会自动检测**主参考图**（即第一个 `--image-url`）的宽高比，并映射到 `agnes-image-2.5-flash` 支持的 8 种官方 ratio 之一（`1:1` / `3:4` / `4:3` / `16:9` / `9:16` / `2:3` / `3:2` / `21:9`），避免输出画布比例与输入主体不一致导致人物变形。

```bash
# 自动检测：会打印 [INFO] Main reference image: ... → auto ratio: ...
python scripts/agnes_client.py image "prompt" --image-url MODEL_URL --image-url REF_URL --size 2K

# 手动指定（跳过自动检测）
python scripts/agnes_client.py image "prompt" --image-url MODEL_URL --ratio 16:9
```

> **主参考图约定**：第一个 `--image-url` 视为决定构图/比例的主体（通常是模特/产品图），第二张及以后视为风格/细节参考。如需切换主参考图，交换 `--image-url` 顺序即可。

## 参考

- API 详细文档: `references/api_reference.md`
- 官网: https://agnes-ai.com/
- API 平台: https://platform.agnes-ai.com/
