#!/usr/bin/env python3
"""
Agnes AI Multimodal Client — 全模态 API 客户端
覆盖：文本生成 / 文生图 / 图生图 / 视频生成(V2.0 与 V2.5 Flash 双引擎) / 关键帧动画 / 自动翻译 / 轮询

使用方法：
  python agnes_client.py text "你的问题"
  python agnes_client.py image "A futuristic city" --size 2K --ratio 16:9
  python agnes_client.py image "一只猫" --image-url "https://example.com/input.png"
  # 视频引擎一：V2.0（默认 5s，自由帧率/分辨率）
  python agnes_client.py video "A sunset over mountains" --poll
  python agnes_client.py video "一段视频" --image-url "https://example.com/frame1.png" --poll
  python agnes_client.py video --keyframes "https://a.com/1.png,https://a.com/2.png" --poll
  # 视频引擎二：Video 2.5 Flash（新一代，text/keyframe/reference 三模式，免费 720P）
  python agnes_client.py video25 "雨后的未来城市街道，霓虹灯倒影，电影级运镜" --poll
  python agnes_client.py video25 "人物自然转身走向窗边" --first-frame "https://a.com/first.png" --last-frame "https://a.com/last.png" --poll
  python agnes_client.py video25 "以 <Picture 1> 的角色为参考，在花田中奔跑" --image-url "https://a.com/char.png" --poll
  python agnes_client.py video-status TASK_ID [--model agnes-video-2.5-flash]
  python agnes_client.py translate "一只在月光下散步的猫"
  python agnes_client.py smoke-test
"""

import argparse
import json
import os
import struct
import sys
import time
import urllib.request
import urllib.error

# ============================================================
# 配置 — API Key 在此处修改
# ============================================================
API_KEY = "YOUR_AGNES_API_KEY_HERE"  # <-- 替换为你的 API Key
BASE_URL = "https://apihub.agnes-ai.com"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# 环境变量回退（如果代码中的 KEY 仍是占位符则从环境变量读取）
if API_KEY == "YOUR_AGNES_API_KEY_HERE":
    API_KEY = os.environ.get("AGNES_API_KEY") or os.environ.get("AGNES_API_TOKEN") or os.environ.get("APIHUB_AGNES_API_KEY") or ""
    HEADERS["Authorization"] = f"Bearer {API_KEY}"

# ============================================================
# 模型常量（2026-09 官网最新免费模型）
# ============================================================
TEXT_MODEL = "agnes-2.5-flash"          # 文本/推理/Vision，$0
IMAGE_MODEL = "agnes-image-2.5-flash"   # 最新一代图像模型（默认，$0），可用 --model 回退 agnes-image-2.1-flash
IMAGE_MODEL_LEGACY = "agnes-image-2.1-flash"  # 上一代图像模型（$0）
VIDEO_V20_MODEL = "agnes-video-v2.0"    # 视频引擎一：V2.0（t2v/ti2vid/keyframes，$0/秒）
VIDEO_V25_FLASH_MODEL = "agnes-video-2.5-flash"  # 视频引擎二：新一代限时免费（仅 720P）
VIDEO_V25_MODEL = "agnes-video-2.5"     # 新一代付费版（960P/2K、支持视频参考）


def api_post(endpoint: str, payload: dict, timeout: int = 120) -> dict:
    """通用 POST 请求"""
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": True, "status": e.code, "body": body}
    except urllib.error.URLError as e:
        return {"error": True, "reason": str(e.reason)}


def api_get(endpoint: str, timeout: int = 30) -> dict:
    """通用 GET 请求"""
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": True, "status": e.code, "body": body}
    except urllib.error.URLError as e:
        return {"error": True, "reason": str(e.reason)}


def api_get_raw(path: str, timeout: int = 30) -> dict:
    """通用 GET 请求（非 /v1/ 前缀路径，如 /agnesapi?video_id=...）"""
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": True, "status": e.code, "body": body}
    except urllib.error.URLError as e:
        return {"error": True, "reason": str(e.reason)}


# ============================================================
# 图片比例自动检测（i2i 主参考图）
# ============================================================
# agnes-image-2.1-flash 支持的官方 ratio 档位 (w:h)
SUPPORTED_RATIOS = {
    "1:1": 1.0,
    "3:4": 3 / 4,
    "4:3": 4 / 3,
    "16:9": 16 / 9,
    "9:16": 9 / 16,
    "2:3": 2 / 3,
    "3:2": 3 / 2,
    "21:9": 21 / 9,
}


def fetch_image_head(url: str, max_bytes: int = 65536, timeout: int = 20) -> bytes:
    """下载图片文件头部字节（PNG/JPEG 尺寸信息都在文件头，无需全量下载）"""
    req = urllib.request.Request(url, headers={"Range": f"bytes=0-{max_bytes - 1}"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(max_bytes)
    except urllib.error.HTTPError:
        # 部分图床不支持 Range，退化为整图下载（仍只保留头部）
        try:
            req2 = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req2, timeout=timeout) as resp:
                return resp.read(max_bytes)
        except Exception:
            return b""
    except Exception:
        return b""


def detect_image_size(url: str) -> tuple:
    """检测图片 URL 的实际像素尺寸，返回 (width, height)；失败返回 None"""
    data = fetch_image_head(url)
    if not data:
        return None

    # PNG: 固定 8 字节签名 + IHDR (13 字节)，宽高在偏移 16-23
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
        return (w, h)

    # JPEG: 扫描 SOF0-SOF3 段（标记 0xC0-0xC3），宽高位于段内偏移 5-8
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
                if seg_len >= 7 and i + 9 <= len(data):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return (w, h)
                i += 2 + seg_len
            else:
                seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
                i += 2 + seg_len
        return None

    return None


def ratio_to_supported(w: int, h: int) -> str:
    """将图片实际宽高比映射到最接近的官方 ratio 档位"""
    actual = w / h
    best_ratio = min(SUPPORTED_RATIOS.items(), key=lambda kv: abs(kv[1] - actual))
    return best_ratio[0]


def auto_detect_ratio(image_urls: list, index: int = 0) -> str:
    """检测主参考图的比例并映射到官方 ratio。返回 ratio 字符串或 None"""
    if not image_urls or index >= len(image_urls):
        return None
    size = detect_image_size(image_urls[index])
    if not size:
        return None
    w, h = size
    ratio = ratio_to_supported(w, h)
    print(f"[INFO] Main reference image: {image_urls[index]} ({w}x{h}) → auto ratio: {ratio}")
    return ratio


# ============================================================
# 自动翻译
# ============================================================
def translate_to_english(text: str) -> str:
    """使用 agnes-2.5-flash 将中文提示词翻译为英文"""
    payload = {
        "model": "agnes-2.5-flash",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a professional prompt translator. "
                    "Translate the user's Chinese prompt into natural, vivid English suitable for AI image/video generation. "
                    "Preserve: subject, scene, style, lighting, composition, camera movement, action descriptions, negative constraints. "
                    "Output ONLY the translated English prompt, nothing else."
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0.3,
        "max_tokens": 500,
    }
    result = api_post("/v1/chat/completions", payload)
    if result.get("error"):
        print(f"[WARN] Translation failed, using original text: {result}", file=sys.stderr)
        return text
    try:
        translated = result["choices"][0]["message"]["content"].strip()
        print(f"[INFO] Translated: {translated}", file=sys.stderr)
        return translated
    except (KeyError, IndexError):
        return text


# ============================================================
# 文本生成
# ============================================================
def generate_text(prompt: str, stream: bool = False, system: str = None, thinking: bool = False, max_tokens: int = 8192):
    """文本生成 — agnes-2.5-flash（支持 Thinking 推理模式）"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "agnes-2.5-flash",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": max_tokens,
        "stream": stream,
    }
    # 2.5 Thinking 模式（编码/推理/多步任务更优，默认关闭）
    if thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": True}

    if stream:
        payload["stream"] = True
        url = f"{BASE_URL}/v1/chat/completions"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=HEADERS, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            for line in resp:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    chunk = line[6:]
                    if chunk == "[DONE]":
                        break
                    try:
                        delta = json.loads(chunk)
                        content = delta["choices"][0]["delta"].get("content", "")
                        if content:
                            sys.stdout.write(content)
                            sys.stdout.flush()
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass
        print()
    else:
        result = api_post("/v1/chat/completions", payload)
        print(json.dumps(result, ensure_ascii=False, indent=2))


# ============================================================
# 文生图 / 图生图
# ============================================================
def generate_image(
    prompt: str,
    image_urls: list = None,
    size: str = "1K",
    ratio: str = None,
    response_format: str = "url",
    no_translate: bool = False,
    model: str = IMAGE_MODEL,
):
    """文生图 & 图生图 — 默认 agnes-image-2.5-flash（可 --model 回退 agnes-image-2.1-flash）

    尺寸建议（2.5 与 2.1 规则一致）:
      - size 使用档位式 1K/2K/3K/4K（推荐），配合 ratio
      - 也兼容 1024x768 等历史精确尺寸，但不支持的精确尺寸会被服务端标准化

    ratio 取值:
      - None / "auto": 自动检测主参考图（第 1 张输入图）比例并映射到官方档位
      - "1:1" / "3:4" / ... : 手动指定官方比例
    """
    # 自动翻译
    if not no_translate and _needs_translation(prompt):
        prompt = translate_to_english(prompt)

    # 自动比例检测：i2i 时未手动指定 ratio，则按主参考图（第一张输入图）比例输出
    if ratio in (None, "auto") and image_urls:
        ratio = auto_detect_ratio(image_urls, index=0)
        if not ratio:
            print("[WARN] Could not auto-detect image ratio, falling back to API default.", file=sys.stderr)

    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
    }
    # 档位式 size (1K/2K/3K/4K) 配合宽高比
    if ratio:
        payload["ratio"] = ratio

    if image_urls:
        payload["extra_body"] = {
            "image": image_urls,
            "response_format": response_format,
        }
    else:
        payload["extra_body"] = {
            "response_format": response_format,
        }

    print(f"[INFO] model={model}, size={size}, ratio={ratio or 'default(1:1)'}, i2i={bool(image_urls)}", file=sys.stderr)
    result = api_post("/v1/images/generations", payload, timeout=180)
    if result.get("error"):
        print(f"ERROR: {json.dumps(result, ensure_ascii=False, indent=2)}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    # 提取并输出图片 URL
    try:
        img_url = result["data"][0]["url"]
        print(f"\n[IMAGE_URL] {img_url}")
    except (KeyError, IndexError):
        pass


# ============================================================
# 视频生成
# ============================================================
def generate_video(
    prompt: str = None,
    image_urls: list = None,
    mode: str = "t2v",          # t2v / ti2vid / keyframes
    num_frames: int = 121,
    frame_rate: int = 24,
    width: int = None,
    height: int = None,
    seed: int = None,
    negative_prompt: str = None,
    num_inference_steps: int = None,
    poll: bool = True,
    no_translate: bool = False,
):
    """视频生成 — 文生视频 / 图生视频 / 关键帧动画

    支持 V2.0 新参数:
      - width/height: 分辨率（自动标准化到 480p/720p/1080p 档位）
      - seed: 随机种子，可复现结果
      - negative_prompt: 反向提示词，避免不需要的内容
      - num_inference_steps: 推理步数
    """
    if prompt and not no_translate and _needs_translation(prompt):
        prompt = translate_to_english(prompt)

    payload = {
        "model": "agnes-video-v2.0",
        "num_frames": num_frames,
        "frame_rate": frame_rate,
    }

    if width:
        payload["width"] = width
    if height:
        payload["height"] = height
    if seed is not None:
        payload["seed"] = seed
    if negative_prompt:
        payload["negative_prompt"] = negative_prompt
    if num_inference_steps:
        payload["num_inference_steps"] = num_inference_steps

    if prompt:
        payload["prompt"] = prompt
    if image_urls:
        if mode == "keyframes":
            payload["image"] = image_urls
            payload["mode"] = "keyframes"
        else:
            # ti2vid: 取第一张作起始帧
            payload["image"] = image_urls[0]
            payload["mode"] = "ti2vid"

    print(f"[INFO] Creating video task... (num_frames={num_frames}, fps={frame_rate}, mode={mode})", file=sys.stderr)
    result = api_post("/v1/videos", payload, timeout=30)
    if result.get("error"):
        print(f"ERROR: {json.dumps(result, ensure_ascii=False, indent=2)}", file=sys.stderr)
        sys.exit(1)

    task_id = result.get("task_id") or result.get("id")
    if not task_id:
        print(f"ERROR: No task_id in response: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Video task created: {task_id}", file=sys.stderr)

    if poll:
        poll_video(task_id)
    else:
        print(json.dumps({"task_id": task_id, "status": "submitted"}, ensure_ascii=False, indent=2))


def poll_video(task_id: str, max_wait: int = 600, interval: int = 5, model_name: str = None):
    """轮询视频任务直到完成（优先 video_id 新接口，回退 task_id 旧接口）

    model_name: 新引擎 (agnes-video-2.5 / agnes-video-2.5-flash) 的 keyframe/reference
                模式必须在查询 URL 中携带 model_name；text 模式可省略。
    """
    print(f"[INFO] Polling video task {task_id} (max {max_wait}s)...", file=sys.stderr)
    start = time.time()

    while time.time() - start < max_wait:
        # 优先: GET /agnesapi?video_id=<ID>[&model_name=<MODEL>]
        query = f"/agnesapi?video_id={task_id}"
        if model_name:
            query += f"&model_name={model_name}"
        result = api_get_raw(query)
        if result.get("error") or not result.get("status"):
            # 兼容旧版: GET /v1/videos/<TASK_ID>
            result = api_get(f"/v1/videos/{task_id}")
        if result.get("error"):
            print(f"[WARN] Poll error: {result}", file=sys.stderr)
            time.sleep(interval)
            continue

        status = result.get("status", "unknown")
        print(f"[INFO] Status: {status} (elapsed: {int(time.time() - start)}s)", file=sys.stderr)

        if status in ("completed", "succeeded", "done"):
            video_url = (
                result.get("video_url")
                or result.get("url")
                or result.get("output_url")
                or (result.get("metadata") or {}).get("url")
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if video_url:
                print(f"\n[VIDEO_URL] {video_url}")
            return result
        elif status in ("failed", "error", "cancelled"):
            print(f"ERROR: Video generation failed: {json.dumps(result, ensure_ascii=False, indent=2)}", file=sys.stderr)
            sys.exit(1)

        time.sleep(interval)

    print(f"ERROR: Video task {task_id} timed out after {max_wait}s", file=sys.stderr)
    sys.exit(1)


def get_video_status(task_id: str, model_name: str = None):
    """查询视频任务状态（优先 video_id 新接口，可携带 model_name）"""
    query = f"/agnesapi?video_id={task_id}"
    if model_name:
        query += f"&model_name={model_name}"
    result = api_get_raw(query)
    if result.get("error") or not result.get("status"):
        result = api_get(f"/v1/videos/{task_id}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    video_url = (
        result.get("video_url")
        or result.get("url")
        or result.get("output_url")
        or (result.get("metadata") or {}).get("url")
    )
    if video_url:
        print(f"\n[VIDEO_URL] {video_url}")


# ============================================================
# 视频引擎二：Agnes Video 2.5 / 2.5 Flash
# ============================================================
def generate_video_v25(
    prompt: str = None,
    mode: str = "auto",   # auto / text / keyframe / reference
    seconds: str = "5",   # "4"-"12"，字符串
    size: str = "720P",   # 2.5-flash 固定 720P；agnes-video-2.5 可选 720P/960P/2K
    aspect_ratio: str = "16:9",
    model: str = VIDEO_V25_FLASH_MODEL,
    first_frame: str = None,
    last_frame: str = None,
    image_urls: list = None,
    audio_urls: list = None,
    seed: int = None,
    poll: bool = True,
    no_translate: bool = False,
):
    """新一代视频生成 — agnes-video-2.5-flash（限时免费）/ agnes-video-2.5（付费）

    模式（mode="auto" 时按素材自动推断）:
      - text:       纯文本生成视频
      - keyframe:   首帧/尾帧控制起止构图（--first-frame / --last-frame，至少一个）
      - reference:  参考图片/音频生成（--image-url 最多5张 / --audio-url 最多3段；Flash 不支持视频参考）

    与 V2.0 引擎差异：参数体系完全不同（seconds/mode/aspect_ratio/size），
    不支持 num_frames/width/height/negative_prompt 等 V2.0 参数（会返回 400）。
    """
    if prompt and not no_translate and _needs_translation(prompt):
        prompt = translate_to_english(prompt)

    # ---- 模式推断 ----
    if mode == "auto":
        if first_frame or last_frame:
            mode = "keyframe"
        elif image_urls or audio_urls:
            mode = "reference"
        else:
            mode = "text"
    elif mode not in ("text", "keyframe", "reference"):
        print(f"ERROR: invalid mode '{mode}' (choose text/keyframe/reference)", file=sys.stderr)
        sys.exit(1)

    # ---- 模式与素材校验 ----
    if mode == "text" and (first_frame or last_frame or image_urls or audio_urls):
        print("ERROR: mode=text 不允许传入 first_frame/last_frame/images/audios", file=sys.stderr)
        sys.exit(1)
    if mode == "keyframe":
        if not (first_frame or last_frame):
            print("ERROR: mode=keyframe 需要 --first-frame 与 --last-frame 至少一个", file=sys.stderr)
            sys.exit(1)
        if image_urls or audio_urls:
            print("ERROR: mode=keyframe 不允许传入 images/audios（请改用 first/last frame）", file=sys.stderr)
            sys.exit(1)
    if mode == "reference":
        if not (image_urls or audio_urls):
            print("ERROR: mode=reference 需要 --image-url 或 --audio-url 至少一个", file=sys.stderr)
            sys.exit(1)
        if first_frame or last_frame:
            print("ERROR: mode=reference 不允许传入 first/last frame（请改用 images/audios）", file=sys.stderr)
            sys.exit(1)
        if model == VIDEO_V25_FLASH_MODEL:
            if image_urls and len(image_urls) > 5:
                print("ERROR: agnes-video-2.5-flash 参考图片最多 5 张", file=sys.stderr)
                sys.exit(1)
            if audio_urls and len(audio_urls) > 3:
                print("ERROR: agnes-video-2.5-flash 参考音频最多 3 段", file=sys.stderr)
                sys.exit(1)
    if model == VIDEO_V25_FLASH_MODEL and size != "720P":
        print("ERROR: agnes-video-2.5-flash 仅支持 size=720P（flash 限制）", file=sys.stderr)
        sys.exit(1)

    # ---- 构建 payload ----
    payload = {
        "model": model,
        "mode": mode,
        "size": size,
        "seconds": str(seconds),
    }
    if prompt:
        payload["prompt"] = prompt
    if aspect_ratio:
        payload["aspect_ratio"] = aspect_ratio
    if seed is not None:
        payload["seed"] = seed

    if first_frame:
        payload["first_frame"] = first_frame
    if last_frame:
        payload["last_frame"] = last_frame
    if image_urls:
        payload["images"] = image_urls
    if audio_urls:
        payload["audios"] = audio_urls

    print(f"[INFO] Creating {model} task... (mode={mode}, seconds={seconds}, size={size}, ratio={aspect_ratio})", file=sys.stderr)
    result = api_post("/v1/videos", payload, timeout=30)
    if result.get("error"):
        print(f"ERROR: {json.dumps(result, ensure_ascii=False, indent=2)}", file=sys.stderr)
        sys.exit(1)

    video_id = result.get("video_id") or result.get("task_id") or result.get("id")
    if not video_id:
        print(f"ERROR: No video_id in response: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] Video task created: {video_id}", file=sys.stderr)

    if poll:
        poll_video(video_id, model_name=model)
    else:
        print(json.dumps({"video_id": video_id, "model": model, "status": result.get("status", "submitted")},
                         ensure_ascii=False, indent=2))


# ============================================================
# 冒烟测试
# ============================================================
def smoke_test():
    """快速验证 API 连通性和基础能力"""
    print("=" * 60)
    print("Agnes AI Multimodal — Smoke Test")
    print("=" * 60)

    # 1. 文本生成
    print("\n[1/5] Text Generation (agnes-2.5-flash)...")
    result = api_post("/v1/chat/completions", {
        "model": TEXT_MODEL,
        "messages": [{"role": "user", "content": "Say 'Hello, Agnes!' in one sentence."}],
        "max_tokens": 50,
    })
    if result.get("error"):
        print(f"  FAIL: {result}", file=sys.stderr)
    else:
        try:
            text = result["choices"][0]["message"]["content"]
            print(f"  OK: {text[:80]}")
        except (KeyError, IndexError):
            print(f"  FAIL: unexpected response structure")

    # 2. 文生图（agnes-image-2.5-flash）
    print(f"\n[2/5] Text-to-Image ({IMAGE_MODEL})...")
    result = api_post("/v1/images/generations", {
        "model": IMAGE_MODEL,
        "prompt": "A simple red circle on white background, minimal",
        "size": "1K",
        "extra_body": {"response_format": "url"},
    }, timeout=180)
    if result.get("error"):
        print(f"  FAIL: {result}", file=sys.stderr)
    else:
        try:
            img_url = result["data"][0]["url"]
            print(f"  OK: {img_url[:80]}...")
        except (KeyError, IndexError):
            print(f"  WARN: no image URL in response")

    # 3. 图生图
    print(f"\n[3/5] Image-to-Image ({IMAGE_MODEL})...")
    print("  (skipped — requires input image URL)")

    # 4. Video 2.5 Flash — text 模式提交（免费 720P，不轮询）
    print(f"\n[4/5] Video 2.5 Flash submit ({VIDEO_V25_FLASH_MODEL})...")
    result = api_post("/v1/videos", {
        "model": VIDEO_V25_FLASH_MODEL,
        "prompt": "A gentle ocean wave rolling onto a sandy beach at golden hour, slow camera drift",
        "mode": "text",
        "size": "720P",
        "seconds": "4",
        "aspect_ratio": "16:9",
    }, timeout=30)
    if result.get("error"):
        print(f"  FAIL: {result}", file=sys.stderr)
    else:
        vid = result.get("video_id") or result.get("task_id") or result.get("id")
        print(f"  OK: video task created: {vid}")
        print(f"  (query later with: python agnes_client.py video-status {vid} --model {VIDEO_V25_FLASH_MODEL})")

    # 5. 翻译
    print("\n[5/5] Auto-Translation...")
    translated = translate_to_english("一只在月光下散步的猫")
    print(f"  Input: 一只在月光下散步的猫")
    print(f"  Output: {translated}")

    print("\n" + "=" * 60)
    print("Smoke test complete.")


# ============================================================
# 图片理解 / Vision
# ============================================================
def analyze_image(
    image_urls: list,
    prompt: str = "Describe this image in detail.",
    system: str = None,
    max_tokens: int = 1000,
    no_translate: bool = False,
):
    """图片理解 — 使用 agnes-2.5-flash 的视觉能力分析图片"""
    if not no_translate and _needs_translation(prompt):
        prompt = translate_to_english(prompt)

    # 构建 Vision API 格式的 content 数组
    content = [{"type": "text", "text": prompt}]
    for url in image_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": content})

    payload = {
        "model": "agnes-2.5-flash",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }

    result = api_post("/v1/chat/completions", payload, timeout=120)
    if result.get("error"):
        print(f"ERROR: {json.dumps(result, ensure_ascii=False, indent=2)}", file=sys.stderr)
        sys.exit(1)

    try:
        description = result["choices"][0]["message"]["content"]
        print(description)
        return description
    except (KeyError, IndexError):
        print(f"ERROR: unexpected response: {json.dumps(result, ensure_ascii=False, indent=2)}", file=sys.stderr)
        sys.exit(1)


# ============================================================
# 工具函数
# ============================================================
def _needs_translation(text: str) -> bool:
    """判断文本是否包含中文（需要翻译）"""
    return any("\u4e00" <= c <= "\u9fff" or "\u3400" <= c <= "\u4dbf" for c in text)


# ============================================================
# CLI 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Agnes AI Multimodal Client — 全模态生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agnes_client.py text "Explain quantum computing in simple terms"
  agnes_client.py text "你好" --stream
  agnes_client.py image "A futuristic city at sunset, cinematic" --size 2K --ratio 16:9
  agnes_client.py image "一只猫" --image-url "https://example.com/input.png"
  agnes_client.py video "A drone flying over mountains" --poll
  agnes_client.py video "一段场景" --image-url "https://example.com/frame.png" --poll
  agnes_client.py video --keyframes "https://a.com/1.png,https://a.com/2.png" --poll
  agnes_client.py video25 "雨后的未来城市街道，电影级运镜" --poll
  agnes_client.py video25 "人物转身走向窗边" --first-frame "https://a.com/f.png" --last-frame "https://a.com/l.png" --poll
  agnes_client.py video25 "以 <Picture 1> 为参考，角色在花田奔跑" --image-url "https://a.com/c.png" --poll
  agnes_client.py video-status TASK_ID --model agnes-video-2.5-flash
  agnes_client.py translate "一只在月光下散步的猫"
  agnes_client.py smoke-test
        """,
    )
    sub = parser.add_subparsers(dest="command", help="Sub-command")

    # text
    p_text = sub.add_parser("text", help=f"Text generation ({TEXT_MODEL})")
    p_text.add_argument("prompt", help="Text prompt")
    p_text.add_argument("--stream", action="store_true", help="Stream output")
    p_text.add_argument("--system", help="System prompt", default=None)
    p_text.add_argument("--thinking", action="store_true", help="Enable Thinking mode (better for coding/reasoning)")
    p_text.add_argument("--max-tokens", type=int, default=8192, help="Max output tokens (default: 8192)")

    # image
    p_img = sub.add_parser("image", help=f"Image generation (default: {IMAGE_MODEL})")
    p_img.add_argument("prompt", help="Image prompt")
    p_img.add_argument("--image-url", action="append", dest="image_urls",
                       help="Input image URL for i2i (can repeat)")
    p_img.add_argument("--size", default="1K",
                       help="Output size: tier (1K/2K/3K/4K, default: 1K) or exact (1024x768, may be standardized)")
    p_img.add_argument("--ratio", default="auto", help="Aspect ratio: auto (detect from main input image, default), or 1:1, 3:4, 4:3, 16:9, 9:16, 2:3, 3:2, 21:9")
    p_img.add_argument("--model", default=IMAGE_MODEL,
                       help=f"Image model (default: {IMAGE_MODEL}; legacy: {IMAGE_MODEL_LEGACY})")
    p_img.add_argument("--no-translate", action="store_true", help="Skip auto-translation")

    # video (V2.0 engine)
    p_vid = sub.add_parser("video", help=f"Video generation V2.0 engine ({VIDEO_V20_MODEL})")
    p_vid.add_argument("prompt", nargs="?", help="Video prompt")
    p_vid.add_argument("--image-url", action="append", dest="image_urls",
                       help="Input image URL for i2v (can repeat)")
    p_vid.add_argument("--keyframes", help="Comma-separated keyframe URLs")
    p_vid.add_argument("--num-frames", type=int, default=121, help="Frame count (8n+1, max 441, default: 121)")
    p_vid.add_argument("--frame-rate", type=int, default=24, help="Frame rate FPS 1-60 (default: 24)")
    p_vid.add_argument("--width", type=int, default=None, help="Video width (auto-mapped to 480p/720p/1080p preset)")
    p_vid.add_argument("--height", type=int, default=None, help="Video height (auto-mapped to preset)")
    p_vid.add_argument("--seed", type=int, default=None, help="Random seed for reproducible results")
    p_vid.add_argument("--negative-prompt", default=None, help="Negative prompt (what to avoid)")
    p_vid.add_argument("--steps", type=int, default=None, dest="num_inference_steps",
                       help="Number of inference steps")
    p_vid.add_argument("--poll", action="store_true", default=True, help="Wait for completion")
    p_vid.add_argument("--no-poll", action="store_true", help="Submit only, don't wait")
    p_vid.add_argument("--no-translate", action="store_true", help="Skip auto-translation")

    # video25 (Video 2.5 / 2.5 Flash engine)
    p_v25 = sub.add_parser("video25",
                           help=f"Video generation 2.5 engine ({VIDEO_V25_FLASH_MODEL} default, free; or {VIDEO_V25_MODEL})")
    p_v25.add_argument("prompt", nargs="?", help="Video prompt (reference mode may use <Picture N>/<Audio N>)")
    p_v25.add_argument("--mode", default="auto",
                       help="Generation mode: auto/text/keyframe/reference (auto infers from media args)")
    p_v25.add_argument("--seconds", default="5", help="Duration 4-12 seconds (string, default: 5)")
    p_v25.add_argument("--size", default="720P", help="Resolution: 720P (flash only supports 720P) / 960P / 2K")
    p_v25.add_argument("--aspect-ratio", default="16:9",
                       help="Aspect ratio: 16:9, 9:16, 1:1, 4:3, 3:4, 21:9 (default: 16:9)")
    p_v25.add_argument("--model", default=VIDEO_V25_FLASH_MODEL,
                       help=f"Video model (default: {VIDEO_V25_FLASH_MODEL}; paid: {VIDEO_V25_MODEL})")
    p_v25.add_argument("--first-frame", default=None, help="First frame URL (keyframe mode)")
    p_v25.add_argument("--last-frame", default=None, help="Last frame URL (keyframe mode)")
    p_v25.add_argument("--image-url", action="append", dest="image_urls",
                       help="Reference image URL (reference mode, flash max 5)")
    p_v25.add_argument("--audio-url", action="append", dest="audio_urls",
                       help="Reference audio URL (reference mode, flash max 3)")
    p_v25.add_argument("--seed", type=int, default=None, help="Random seed for reproducible results")
    p_v25.add_argument("--poll", action="store_true", default=True, help="Wait for completion")
    p_v25.add_argument("--no-poll", action="store_true", help="Submit only, don't wait")
    p_v25.add_argument("--no-translate", action="store_true", help="Skip auto-translation")

    # video-status
    p_vs = sub.add_parser("video-status", help="Query video task status")
    p_vs.add_argument("task_id", help="Video task ID")
    p_vs.add_argument("--model", default=None,
                      help=f"Model name for query (e.g. {VIDEO_V25_FLASH_MODEL}); required for 2.5 keyframe/reference tasks")

    # translate
    p_tr = sub.add_parser("translate", help="Translate Chinese prompt to English")
    p_tr.add_argument("text", help="Text to translate")

    # smoke-test
    sub.add_parser("smoke-test", help="Run smoke test")

    # vision — 图片理解
    p_vis = sub.add_parser("vision", help="Image understanding via agnes-2.5-flash Vision API")
    p_vis.add_argument("--image-url", action="append", dest="image_urls", required=True,
                       help="Image URL to analyze (can repeat for multiple)")
    p_vis.add_argument("--prompt", default="Describe this image in detail.",
                       help="Analysis prompt (default: describe in detail)")
    p_vis.add_argument("--system", default=None, help="System prompt")
    p_vis.add_argument("--max-tokens", type=int, default=1000, help="Max output tokens")
    p_vis.add_argument("--no-translate", action="store_true", help="Skip auto-translation")

    args = parser.parse_args()

    if args.command == "text":
        generate_text(args.prompt, stream=args.stream, system=args.system,
                      thinking=args.thinking, max_tokens=args.max_tokens)
    elif args.command == "image":
        generate_image(
            args.prompt,
            image_urls=args.image_urls,
            size=args.size,
            ratio=args.ratio,
            no_translate=args.no_translate,
            model=args.model,
        )
    elif args.command == "video":
        if args.no_poll:
            poll_flag = False
        else:
            poll_flag = args.poll

        # Determine mode
        keyframe_urls = None
        if args.keyframes:
            keyframe_urls = [u.strip() for u in args.keyframes.split(",") if u.strip()]
            mode = "keyframes"
        elif args.image_urls:
            mode = "ti2vid"
        else:
            mode = "t2v"

        generate_video(
            prompt=args.prompt,
            image_urls=keyframe_urls or args.image_urls,
            mode=mode,
            num_frames=args.num_frames,
            frame_rate=args.frame_rate,
            width=args.width,
            height=args.height,
            seed=args.seed,
            negative_prompt=args.negative_prompt,
            num_inference_steps=args.num_inference_steps,
            poll=poll_flag,
            no_translate=args.no_translate,
        )
    elif args.command == "video25":
        if args.no_poll:
            poll_flag = False
        else:
            poll_flag = args.poll
        generate_video_v25(
            prompt=args.prompt,
            mode=args.mode,
            seconds=args.seconds,
            size=args.size,
            aspect_ratio=args.aspect_ratio,
            model=args.model,
            first_frame=args.first_frame,
            last_frame=args.last_frame,
            image_urls=args.image_urls,
            audio_urls=args.audio_urls,
            seed=args.seed,
            poll=poll_flag,
            no_translate=args.no_translate,
        )
    elif args.command == "video-status":
        get_video_status(args.task_id, model_name=args.model)
    elif args.command == "translate":
        result = translate_to_english(args.text)
        print(result)
    elif args.command == "smoke-test":
        smoke_test()
    elif args.command == "vision":
        analyze_image(
            image_urls=args.image_urls,
            prompt=args.prompt,
            system=args.system,
            max_tokens=args.max_tokens,
            no_translate=args.no_translate,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
