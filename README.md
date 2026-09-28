# Agnes Multimodal — WorkBuddy 全模态 AI 生成 Skill

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-WorkBuddy-orange)](https://www.codebuddy.cn/)

封装 [Agnes AI (Sapiens AI)](https://agnes-ai.com/) 全部生成能力的 **WorkBuddy 专用 Skill**。一个脚本搞定文本、图片、视频、视觉理解，自动中译英，零外部依赖。

---

## 能力矩阵

| 能力 | 模型 | 状态 |
|------|------|:--:|
| 📝 文本生成 | `agnes-2.5-flash` (可选 `agnes-3.0-flash`) | ✅ |
| 🧠 推理模式 (Thinking) | `agnes-2.5-flash` | ✅ |
| 🖼️ 文生图 | `agnes-image-2.5-flash` (可回退 2.1) | ✅ |
| 🔄 图生图 | `agnes-image-2.5-flash` (自动比例) | ✅ |
| 👁️ 图片理解 (Vision) | `agnes-2.5-flash` / `agnes-3.0-flash` | ✅ |
| 🎬 文生视频 | `agnes-video-2.5-flash` (text，免费 720P) | ✅ |
| 🎞️ 图生视频 / 参考图 | `video25 --image-url` (reference) | ✅ |
| 🔗 关键帧/首尾帧 | `video25 --first/last-frame` | ✅ |
| 🌐 自动中译英 | `agnes-2.5-flash` | ✅ |
| ⏳ 异步轮询 | — | ✅ |

---

## 安装

### 方式一：WorkBuddy Skill 安装（推荐）

```bash
# 在 WorkBuddy 中通过技能市场搜索 "agnes-multimodal" 安装
# 或从本地导入 .skill 文件
```

### 方式二：手动安装

```bash
# 克隆仓库到 WorkBuddy skills 目录
git clone https://github.com/YOUR_USERNAME/agnes-multimodal.git \
  ~/.workbuddy/skills/agnes-multimodal
```

### 配置 API Key

在 `~/.workbuddy/skills/agnes-multimodal/scripts/agnes_client.py` 中修改：

```python
API_KEY = "YOUR_AGNES_API_KEY_HERE"  # 替换为你的 API Key
```

或设置环境变量（自动回退）：

```bash
# PowerShell
$env:AGNES_API_KEY = "你的API_Key"

# 或持久化
[Environment]::SetEnvironmentVariable("AGNES_API_KEY", "你的API_Key", "User")
```

> 支持的环境变量名：`AGNES_API_KEY` / `AGNES_API_TOKEN` / `APIHUB_AGNES_API_KEY`

---

## 快速开始

```bash
cd ~/.workbuddy/skills/agnes-multimodal
python scripts/agnes_client.py smoke-test
```

---

## CLI 命令速查

```bash
# 文本生成
python scripts/agnes_client.py text "解释量子计算"
python scripts/agnes_client.py text "你好" --stream
python scripts/agnes_client.py text "帮我调试这段代码" --thinking  # 2.5 推理模式
python scripts/agnes_client.py text "复杂推理题" --model agnes-3.0-flash  # 可选 3.0（512K 上下文）

# 文生图（支持档位式尺寸 + 宽高比）
python scripts/agnes_client.py image "A futuristic city at sunset, cinematic" --size 2K --ratio 16:9
python scripts/agnes_client.py image "一只在月光下散步的猫"
python scripts/agnes_client.py image "Cinematic hero image" --size 2K --ratio 16:9

# 图生图
python scripts/agnes_client.py image "Transform to cyberpunk night" --image-url "https://example.com/input.png"

# 图片理解 / Vision
python scripts/agnes_client.py vision --image-url "https://example.com/photo.png"
python scripts/agnes_client.py vision --image-url URL --prompt "这是什么品牌的手表？"
python scripts/agnes_client.py vision --image-url "D:\\pics\\watch.png" --model agnes-3.0-flash  # 更快

# 文生视频（默认免费引擎 Video 2.5 Flash，720P）
python scripts/agnes_client.py video25 "A drone flying over mountains at sunrise" --poll

# 参考图生成（提示词用 <Picture N> 指代素材）
python scripts/agnes_client.py video25 "以 <Picture 1> 的角色为参考在花田奔跑" --image-url "https://example.com/char.png" --poll

# 首尾帧控制
python scripts/agnes_client.py video25 "角色自然转身走向窗边" --first-frame "https://a.com/f.png" --last-frame "https://a.com/l.png" --poll

# 只提交不等待
python scripts/agnes_client.py video25 "..." --no-poll

# 查询视频状态（keyframe/reference 任务必须带 --model）
python scripts/agnes_client.py video-status TASK_ID --model agnes-video-2.5-flash

# 中译英
python scripts/agnes_client.py translate "一只在月光下散步的猫"
```

---

## 特色功能

### 👁️ Vision 桥接 — 给任意模型"看"图片

`agnes-2.5-flash` / `agnes-3.0-flash` 支持 OpenAI Vision API 格式。通过 `vision` 命令，可以先将图片转为文字描述，再传给任意不具备视觉能力的模型（3.0-flash 更快，实测更不易超时）：

```
图片 → vision 命令 → 文字描述 → 任意文本模型继续分析
```

### 🌐 自动翻译

中文提示词自动调用 `agnes-2.5-flash` 翻译为英文，保留主体、场景、风格、光照等关键信息。使用 `--no-translate` 可跳过。

### ⚡ 零依赖

纯 Python 标准库实现（`urllib` + `json` + `argparse`），无需 `pip install` 任何包。

---

## 视频参数约束

| 参数 | 约束 |
|------|------|
| 引擎 | `agnes-video-2.5-flash`（默认，免费，仅 720P） |
| `seconds` | 字符串 `"4"`~`"12"`，默认 `"5"` |
| `size` | flash 固定 `720P`；付费 `agnes-video-2.5` 可选 `720P`/`1080P`/`1K`/`2K` |
| `aspect_ratio` | `21:9` / `16:9`(默认) / `4:3` / `1:1` / `3:4` / `9:16` |
| flash 限制 | 参考图 ≤5 张、音频 ≤3 段、不支持视频参考 |
| 轮询超时 | 默认 600s |

---

## 价格

| 模型 | 定价 |
|------|------|
| `agnes-2.5-flash` (文本/Vision，默认) | 免费 |
| `agnes-3.0-flash` (文本/Vision，可选) | 免费 (512K 上下文) |
| `agnes-image-2.5-flash` / `agnes-image-2.1-flash` (图片) | **免费** |
| `agnes-video-2.5-flash` (视频，**默认**) | **限时免费** (仅 720P) |
| `agnes-video-2.5` (视频，付费，需 `--allow-paid`) | $0.025/秒(720P) / $0.040/秒(1080P、1K) / $0.055/秒(2K) |

---

## 已知限制

- Tool Calling (function calling) 可能不稳定
- 视频生成偶有服务端 `division by zero` 错误
- 图片 API 输入**同时支持公网 URL 和 base64 Data URI**（官网 `image` 数组原文 "Supports public URLs or Data URI Base64"）；CLI 的本地文件路径会自动转 Data URI，无需先传图床
- 视频媒体字段（first_frame/last_frame/images）官网仅背书公网 URL，本地路径转 base64 属未文档化行为，失败请回退公网 URL
- `agnes-video-v2.0` 已于 2026-09-25 官方下线，本 skill 已彻底移除其入口
- 付费视频模型 `agnes-video-2.5` 默认被拦截，须显式 `--allow-paid` 才会调用

---

## 与原始项目的区别

本项目受 [Yacey/agnes-ai-generation-skill](https://github.com/Yacey/agnes-ai-generation-skill) 启发，针对 WorkBuddy 环境进行了以下改进：

| 维度 | 原始项目 | agnes-multimodal |
|------|---------|-----------------|
| 目标平台 | 通用 Agent (Codex/Claude/OpenClaw) | **WorkBuddy** |
| Vision 能力 | ❌ | ✅ 新增 |
| 独立翻译命令 | ❌ | ✅ 新增 |
| 视频模式修正 | — | ✅ `i2v` → `ti2vid` |
| 外部依赖 | — | ✅ 零依赖 (纯 stdlib) |

---

## 致谢

- [Yacey/agnes-ai-generation-skill](https://github.com/Yacey/agnes-ai-generation-skill) — 原始 Skill 实现，提供了 API 结构和设计参考
- [Agnes AI / Sapiens AI](https://agnes-ai.com/) — 底层模型和 API 提供方

---

## License

MIT License — 详见 [LICENSE](LICENSE)
