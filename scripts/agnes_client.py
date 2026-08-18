#!/usr/bin/env python3
"""
Agnes AI Multimodal Client — 全模态 API 客户端
覆盖：文本生成 / 文生图 / 图生图 / 文生视频 / 图生视频 / 关键帧动画 / 自动翻译 / 轮询

使用方法：
  python agnes_client.py text "你的问题"
  python agnes_client.py image "A futuristic city" --size 1024x768
  python agnes_client.py image "一只猫" --image-url "https://example.com/input.png"
  python agnes_client.py video "A sunset over mountains" --poll
  python agnes_client.py video "一段视频" --image-url "https://example.com/frame1.png" --poll
  python agnes_client.py video --keyframes "https://a.com/1.png,https://a.com/2.png" --poll
  python agnes_client.py video-status TASK_ID
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
    size: str = "1024x768",
    ratio: str = None,
    response_format: str = "url",
    no_translate: bool = False,
):
    """文生图 & 图生图 — agnes-image-2.1-flash

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
        "model": "agnes-image-2.1-flash",
        "prompt": prompt,
        "size": size,
    }
    # 2.1 新增：档位式 size (1K/2K/3K/4K) 配合宽高比
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


def poll_video(task_id: str, max_wait: int = 600, interval: int = 5):
    """轮询视频任务直到完成（优先 video_id 新接口，回退 task_id 旧接口）"""
    print(f"[INFO] Polling video task {task_id} (max {max_wait}s)...", file=sys.stderr)
    start = time.time()

    while time.time() - start < max_wait:
        # V2.0 推荐: GET /agnesapi?video_id=<ID>
        result = api_get_raw(f"/agnesapi?video_id={task_id}")
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


def get_video_status(task_id: str):
    """查询视频任务状态（优先 video_id 新接口）"""
    result = api_get_raw(f"/agnesapi?video_id={task_id}")
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
# 冒烟测试
# ============================================================
def smoke_test():
    """快速验证 API 连通性和基础能力"""
    print("=" * 60)
    print("Agnes AI Multimodal — Smoke Test")
    print("=" * 60)

    # 1. 文本生成
    print("\n[1/4] Text Generation (agnes-2.5-flash)...")
    result = api_post("/v1/chat/completions", {
        "model": "agnes-2.5-flash",
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

    # 2. 文生图
    print("\n[2/4] Text-to-Image (agnes-image-2.1-flash)...")
    result = api_post("/v1/images/generations", {
        "model": "agnes-image-2.1-flash",
        "prompt": "A simple red circle on white background, minimal",
        "size": "256x256",
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
    print("\n[3/4] Image-to-Image (agnes-image-2.1-flash)...")
    print("  (skipped — requires input image URL)")

    # 4. 翻译
    print("\n[4/4] Auto-Translation...")
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
  agnes_client.py image "A futuristic city at sunset, cinematic" --size 1024x768
  agnes_client.py image "一只猫" --image-url "https://example.com/input.png"
  agnes_client.py video "A drone flying over mountains" --poll
  agnes_client.py video "一段场景" --image-url "https://example.com/frame.png" --poll
  agnes_client.py video --keyframes "https://a.com/1.png,https://a.com/2.png" --poll
  agnes_client.py video-status TASK_ID
  agnes_client.py translate "一只在月光下散步的猫"
  agnes_client.py smoke-test
        """,
    )
    sub = parser.add_subparsers(dest="command", help="Sub-command")

    # text
    p_text = sub.add_parser("text", help="Text generation (agnes-2.5-flash)")
    p_text.add_argument("prompt", help="Text prompt")
    p_text.add_argument("--stream", action="store_true", help="Stream output")
    p_text.add_argument("--system", help="System prompt", default=None)
    p_text.add_argument("--thinking", action="store_true", help="Enable Thinking mode (better for coding/reasoning)")
    p_text.add_argument("--max-tokens", type=int, default=8192, help="Max output tokens (default: 8192)")

    # image
    p_img = sub.add_parser("image", help="Image generation (agnes-image-2.1-flash)")
    p_img.add_argument("prompt", help="Image prompt")
    p_img.add_argument("--image-url", action="append", dest="image_urls",
                       help="Input image URL for i2i (can repeat)")
    p_img.add_argument("--size", default="1024x768", help="Output size: exact (1024x768) or tier (1K/2K/3K/4K, default: 1024x768)")
    p_img.add_argument("--ratio", default="auto", help="Aspect ratio: auto (detect from main input image, default), or 1:1, 3:4, 4:3, 16:9, 9:16, 2:3, 3:2, 21:9")
    p_img.add_argument("--no-translate", action="store_true", help="Skip auto-translation")

    # video
    p_vid = sub.add_parser("video", help="Video generation (agnes-video-v2.0)")
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

    # video-status
    p_vs = sub.add_parser("video-status", help="Query video task status")
    p_vs.add_argument("task_id", help="Video task ID")

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
    elif args.command == "video-status":
        get_video_status(args.task_id)
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
