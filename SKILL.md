---
name: agnes-multimodal
description: >
  Agnes AI 全模态生成技能。覆盖文本生成(agnes-2.5-flash)、文生图(agnes-image-2.1-flash)、
  图生图、文生视频、图生视频、关键帧动画、自动中译英、异步轮询。一个 Skill 全部搞定。 当用户需要 AI 生成文本、图片、视频，或提到
  "Agnes"、"agnes"、"AI 画图"、"AI 生成视频"、 "AI 图片"、"文生图"、"图生图"、"文生视频"、"关键帧动画"、"用 Agnes
  生成" 时触发。 API Key 默认从环境变量 AGNES_API_KEY 读取，也可在 agnes_client.py 中硬编码。
disable-model-invocation: true
---

# Agnes AI 全模态生成 Skill

## 概述

本 Skill 封装了 Agnes AI (Sapiens AI) 的全部生成能力，通过一个 CLI 脚本统一调用：

- **文本生成**: `agnes-2.5-flash`（支持 Thinking 推理模式）
- **图片理解/Vision**: `agnes-2.5-flash`（OpenAI Vision API 兼容，可分析图片内容）
- **文生图**: `agnes-image-2.1-flash`（高信息密度优化）
- **图生图**: `agnes-image-2.1-flash`（保持构图）
- **文生视频**: `agnes-video-v2.0`
- **图生视频**: `agnes-video-v2.0`
- **关键帧动画**: `agnes-video-v2.0` + 多图输入
- **自动翻译**: 中文提示词自动译英文后调用 API
- **异步轮询**: 视频任务自动轮询直到完成

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

# 文生图
python scripts/agnes_client.py image "A futuristic city at sunset, cinematic realism" --size 1024x768
python scripts/agnes_client.py image "一只在月光下散步的猫"

# 图生图（自动比例检测 — 默认按主参考图比例输出）
python scripts/agnes_client.py image "Transform to cyberpunk night" --image-url "https://...input.png" --image-url "https://...ref.png"

# 图生图 + 手动指定 ratio（不自动检测）
python scripts/agnes_client.py image "Transform to cyberpunk night" --image-url "https://...input.png" --ratio 16:9

# 文生视频（自动轮询）
python scripts/agnes_client.py video "A drone flying over mountains at sunrise" --poll

# 图生视频
python scripts/agnes_client.py video "Add motion to this scene" --image-url "https://...frame.png" --poll

# 关键帧动画
python scripts/agnes_client.py video --keyframes "https://a.com/1.png,https://a.com/2.png,https://a.com/3.png" --poll

# 只提交视频任务不等待
python scripts/agnes_client.py video "..." --no-poll

# 查询视频任务状态
python scripts/agnes_client.py video-status TASK_ID

# 翻译中文提示词
python scripts/agnes_client.py translate "一只猫"

# 图片理解 / Vision（用 agnes-2.5-flash 分析图片内容）
python scripts/agnes_client.py vision --image-url "https://example.com/photo.png"
python scripts/agnes_client.py vision --image-url "https://example.com/photo.png" --prompt "What brand is this watch?"

# 冒烟测试（验证 API 连通性）
python scripts/agnes_client.py smoke-test
```

## 完整工作流

### 文生图流程

1. 接收用户的中文/英文提示词
2. 若含中文且未指定 `--no-translate`，自动调用 `agnes-2.5-flash` 翻译为英文
3. 调用 `POST /v1/images/generations`（模型: `agnes-image-2.1-flash`）
4. 从响应 `data[0].url` 提取图片 URL
5. 将结果返回给用户（显示 URL，或尝试用 `curl`/浏览器打开）

### 图生图流程

1. 确认用户提供了输入图片 URL 或本地路径
2. 如需翻译提示词，执行翻译
3. 调用同一 endpoint，在 `extra_body.image` 中传入输入图片 URL 数组
4. 返回生成结果

### 视频生成流程

1. 确定模式: t2v / ti2vid / keyframes（注意：图生视频 mode 为 `ti2vid`，不是 `i2v`）
2. 提交 `POST /v1/videos` 获取 `task_id`
3. 轮询 `GET /v1/videos/{task_id}`（默认间隔 5s，最长 600s）
4. 状态变为 `completed` 后提取 `video_url`
5. 返回 MP4 视频下载链接

### 视频参数约束

- `num_frames` 必须满足 `8n + 1`，最大 441
- 默认: `num_frames=121, frame_rate=24`（约 5 秒）
- 快速测试用 `--num-frames 81`（约 3.4 秒）

### 图片理解 (Vision) 流程

`agnes-2.5-flash` 支持 OpenAI Vision API 格式的多模态输入，可分析图片内容并返回文字描述。这是"给不具备视觉能力的模型提供眼睛"的桥接方案。2.5 版本的图像理解能力比 2.0 更强，细节识别更准确。

1. 确保图片已上传到可公网访问的 HTTP(S) URL
2. 调用 `vision` 命令，传入图片 URL + 可选的分析提示词
3. 返回文字描述，可直接作为上下文传给其他模型（如"请对这张图片中的手表设计给出改进建议"——先 vision 获取描述，再传给任意文本模型分析）

Vision 命令参数：
- `--image-url`（必填，可多次指定）: 要分析的图片 URL
- `--prompt`（可选）: 分析提示词，默认 "Describe this image in detail."
- `--system`（可选）: 系统提示词
- `--max-tokens`（可选）: 最大输出 tokens，默认 1000
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
| `agnes-2.5-flash` (文本/Vision/推理) | **免费** ($0/1M tokens) |
| `agnes-image-2.1-flash` (图片) | **免费** ($0/image) |
| `agnes-video-v2.0` (视频) | 请查阅官网最新定价 |

## 已知限制

- 2.5 Thinking 模式会返回 `reasoning_content` 字段（思考过程），会增加少量输出 token
- 视频生成偶有 `division by zero` 服务端错误
- 多图视频/关键帧动画尚未完整端到端验证
- 图片 API 仅接受 HTTP(S) URL 作为输入，不支持 base64

## 自动比例检测（i2i）

i2i 时若未指定 `--ratio`，脚本会自动检测**主参考图**（即第一个 `--image-url`）的宽高比，并映射到 `agnes-image-2.1-flash` 支持的 8 种官方 ratio 之一（`1:1` / `3:4` / `4:3` / `16:9` / `9:16` / `2:3` / `3:2` / `21:9`），避免输出画布比例与输入主体不一致导致人物变形。

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
