import base64
import json
import mimetypes
import os
import time
from typing import Any, Dict, Optional, Tuple

import requests
from dotenv import load_dotenv
try:
    import fal_client  # optional official client
except Exception:  # pragma: no cover
    fal_client = None


FAL_KEY_ENV = "FAL_KEY"
load_dotenv()

# Direct invoke endpoint (blocks until result is ready)
FAL_INVOKE_URL = "https://fal.run/fal-ai/kling-video/v2.1/pro/image-to-video"


class FalKlingError(Exception):
    pass


def _get_fal_key() -> str:
    fal_key = os.getenv(FAL_KEY_ENV)
    if not fal_key:
        raise FalKlingError(
            f"Environment variable {FAL_KEY_ENV} is not set. Set it to your FAL API key."
        )
    return fal_key


def _guess_mime_type(file_path: str) -> str:
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        # Default to jpeg if unknown
        return "image/jpeg"
    return mime_type


def encode_image_to_data_uri(image_path: str) -> str:
    if not os.path.isfile(image_path):
        raise FalKlingError(f"Image not found: {image_path}")

    mime_type = _guess_mime_type(image_path)
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def _build_prompt(description: str) -> str:
    suffix = (
        " Move camera towards right, 360 degree to come back to same position. No humans in the office. No moving objects as the camera is panning. "
    )
    description = (description or "").strip()
    if description and not description.endswith("."):
        description = description + "."
    return (description + " " + suffix).strip()


def _make_headers(fal_key: str, content_type_json: bool = True) -> Dict[str, str]:
    headers = {
        # Try Bearer first (current docs)
        "Authorization": f"Bearer {fal_key}",
    }
    if content_type_json:
        headers["Content-Type"] = "application/json"
    return headers


def _extract_video_url_from_result(result_json: Dict) -> Optional[str]:
    # Common shapes: { data: { video: { url }}} or { video: { url } } or { video_url }
    if not isinstance(result_json, dict):
        return None

    candidates = []
    candidates.append(result_json)
    if "data" in result_json and isinstance(result_json["data"], dict):
        candidates.append(result_json["data"])

    for obj in candidates:
        # video.url
        video_obj = obj.get("video") if isinstance(obj, dict) else None
        if isinstance(video_obj, dict):
            url_val = video_obj.get("url")
            if isinstance(url_val, str):
                return url_val
        # direct keys
        for key in ("video_url", "url"):
            val = obj.get(key) if isinstance(obj, dict) else None
            if isinstance(val, str) and val.startswith("http"):
                return val

    return None


def generate_video(
    image_path: str,
    description: str,
    duration_seconds: int = 5,
    cfg_scale: float = 0.5,
    negative_prompt: str = "blur, distort, and low quality",
    prompt_override: Optional[str] = None,
    tail_image_path: Optional[str] = None,
) -> Tuple[Dict, str]:
    """
    Invoke Kling 2.1 (pro) Image-to-Video with the same image as head and tail.

    Returns a tuple: (raw_result_json, video_url)
    """
    if duration_seconds not in (5, 10):
        raise FalKlingError("duration_seconds must be 5 or 10")

    fal_key = _get_fal_key()
    image_data_uri = encode_image_to_data_uri(image_path)
    tail_image_data_uri = (
        encode_image_to_data_uri(tail_image_path) if tail_image_path else image_data_uri
    )
    prompt = prompt_override if prompt_override else _build_prompt(description)
    # prompt = "A modern glass-walled office with racing posters, sleek furniture, glass walls. Move camera towards right, 360 degree to come back to same position. No humans in the office. No moving objects as the camera is panning. Still Office."

    

    # 1) Preferred: use official fal_client if present
    if fal_client and fal_key:
        try:
            if hasattr(fal_client, "set_api_key"):
                fal_client.set_api_key(fal_key)
            args = {
                "prompt": prompt,
                "image_url": image_data_uri,
                "tail_image_url": tail_image_data_uri,
                "duration": str(duration_seconds),  # "5" or "10"
                "negative_prompt": negative_prompt,
                "cfg_scale": float(cfg_scale),
            }
            handler = fal_client.submit(
                "fal-ai/kling-video/v2.1/pro/image-to-video",
                arguments=args,
            )
            result = handler.get()
            if isinstance(result, dict):
                url = _extract_video_url_from_result(result)
                if url:
                    return {"result": result, "prompt": prompt}, url
        except Exception as e:  # fallback to HTTP
            pass

    # 2) HTTP fallback: some invoke endpoints expect top-level fields, not {input: {..}}
    payload_top = {
        "prompt": prompt,
        "image_url": image_data_uri,
        "tail_image_url": tail_image_data_uri,
        "duration": str(duration_seconds),
        "negative_prompt": negative_prompt,
        "cfg_scale": float(cfg_scale),
    }
    headers = _make_headers(fal_key)
    response = requests.post(
        FAL_INVOKE_URL, headers=headers, data=json.dumps(payload_top), timeout=600
    )

    if response.status_code in (401, 403):
        headers = {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}
        response = requests.post(FAL_INVOKE_URL, headers=headers, data=json.dumps(payload_top), timeout=600)

    if response.status_code != 200:
        raise FalKlingError(
            f"FAL request failed: {response.status_code} {response.text[:500]}"
        )

    try:
        result_json = response.json()
    except Exception:
        raise FalKlingError("Failed to parse JSON response from FAL")

    video_url = _extract_video_url_from_result(result_json)
    if not video_url:
        raise FalKlingError(
            f"Could not find video URL in response. Raw keys: {list(result_json.keys())}"
        )

    return {"result": result_json, "prompt": prompt}, video_url


def download_file(url: str, output_path: str) -> None:
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def generate_and_save(
    image_path: str,
    description: str,
    output_path: str,
    duration_seconds: int = 5,
    cfg_scale: float = 0.5,
    negative_prompt: str = "blur, distort, and low quality",
    prompt_override: Optional[str] = None,
    tail_image_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    High-level helper: generates the video and saves it to output_path.
    Returns the output_path on success.
    """
    meta, video_url = generate_video(
        image_path=image_path,
        description=description,
        duration_seconds=duration_seconds,
        cfg_scale=cfg_scale,
        negative_prompt=negative_prompt,
        prompt_override=prompt_override,
        tail_image_path=tail_image_path,
    )
    download_file(video_url, output_path)
    return {
        "output_path": output_path,
        "video_url": video_url,
        "prompt": meta.get("prompt"),
        "raw": meta.get("result"),
    }


