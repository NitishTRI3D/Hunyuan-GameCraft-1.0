from __future__ import annotations
import io
import json
import os
import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import re

from PIL import Image
from dotenv import load_dotenv

load_dotenv()


try:  # Optional dependencies
    import cv2  # type: ignore
except Exception:
    cv2 = None  # type: ignore

try:
    import google.generativeai as genai  # type: ignore
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False


def _frame_to_pil(frame_bgr) -> Image.Image:
    import numpy as np  # local import to avoid hard dep in non-video flows
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def _pil_diff_score(img_a: Image.Image, img_b: Image.Image) -> float:
    # Simple normalized mean absolute difference in RGB space
    import numpy as np
    a = np.asarray(img_a.resize((256, 256)).convert("RGB"), dtype="float32")
    b = np.asarray(img_b.resize((256, 256)).convert("RGB"), dtype="float32")
    diff = np.abs(a - b).mean() / 255.0
    # Clamp to [0,1]
    return float(max(0.0, min(1.0, diff)))


def _sample_video_frames(video_path: str, max_frames: int = 4) -> Tuple[List[Image.Image], List[int]]:
    if cv2 is None:
        raise RuntimeError("OpenCV is required for video analysis but is not installed.")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {video_path}")

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if frame_count <= 0:
        # Read a few frames sequentially if metadata missing
        frames = []
        idxs = []
        i = 0
        while i < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            frames.append(_frame_to_pil(frame))
            idxs.append(i)
            i += 1
        cap.release()
        return frames, idxs

    # Evenly sample indices including first and last
    step = max(1, frame_count // (max_frames - 1) if max_frames > 1 else frame_count)
    indices = sorted({0, frame_count - 1} | {min(frame_count - 1, i * step) for i in range(1, max_frames - 1)})

    frames: List[Image.Image] = []
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if ok:
            frames.append(_frame_to_pil(frame))
        else:
            # Fallback: try to read next available
            ok2, frame2 = cap.read()
            if ok2:
                frames.append(_frame_to_pil(frame2))
            else:
                # Break if nothing can be read
                break
    cap.release()
    # Adjust indices length if fewer frames read
    indices = indices[: len(frames)]
    return frames, indices


def _build_gemini_prompt(original_prompt: str) -> str:
    return (
        "You are evaluating whether a generated video shows actual camera motion vs a static still image loop.\n"
        "You will be given two or more frames sampled from the video.\n"
        "Determine if there is camera movement or visual change across frames.\n\n"
        f"Original scene description: \"{original_prompt}\"\n\n"
        "Respond with ONLY JSON in this exact schema:\n"
        "{\n"
        "  \"has_motion\": true/false,\n"
        "  \"confidence\": 0.0-1.0,\n"
        "  \"reasoning\": \"brief explanation\"\n"
        "}"
    )


def _gemini_check(frames: List[Image.Image], original_prompt: str) -> Tuple[bool, Dict[str, Any]]:
    if not GEMINI_AVAILABLE:
        return False, {"error": "Gemini SDK not available"}
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return False, {"error": "GEMINI_API_KEY not set"}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash-exp")

    # Build a side-by-side strip of up to 3 frames for compactness
    use_frames = frames[:3] if len(frames) >= 3 else frames
    widths, heights = zip(*(im.size for im in use_frames))
    strip = Image.new("RGB", (sum(widths), max(heights)))
    x = 0
    for im in use_frames:
        strip.paste(im.resize((im.size[0], strip.size[1])), (x, 0))
        x += im.size[0]

    prompt = _build_gemini_prompt(original_prompt)

    # Try different input methods as in evaluators.py
    try:
        response = model.generate_content([prompt, strip])
    except Exception as e1:
        try:
            buf = io.BytesIO()
            strip.save(buf, format="JPEG")
            buf.seek(0)
            response = model.generate_content([prompt, buf.getvalue()])
        except Exception as e2:
            return False, {"error": f"Gemini call failed: {e1}; {e2}", "prompt": prompt}

    text = getattr(response, "text", "") or ""
    raw = text.strip()
    # Remove code fences like ```json ... ``` or ``` ... ```
    clean = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw, flags=re.MULTILINE)
    clean = clean.strip()
    # Try direct JSON parse
    try:
        data = json.loads(clean)
        return True, {"prompt": prompt, "response_text": raw, "parsed": data}
    except Exception:
        # Try to extract JSON object substring
        try:
            m = re.search(r"\{[\s\S]*\}", clean)
            if m:
                candidate = m.group(0)
                data = json.loads(candidate)
                return True, {"prompt": prompt, "response_text": raw, "parsed": data}
        except Exception:
            pass
    # Return raw text if not JSON
    return True, {"prompt": prompt, "response_text": raw, "parsed": None}


def analyze_video_motion(
    video_path: str,
    original_image_path: Optional[str],
    kling_prompt: str,
    description: str,
    generation_seconds: float,
    use_gemini: bool = True,
) -> Dict[str, Any]:
    frames, indices = _sample_video_frames(video_path, max_frames=4)
    if not frames:
        raise RuntimeError("No frames could be read from the video for analysis")

    base = frames[0]
    diffs = [0.0]
    for i in range(1, len(frames)):
        diffs.append(_pil_diff_score(base, frames[i]))

    motion_score = max(diffs) if diffs else 0.0
    # Threshold: if max diff < 0.02, consider static; else motion
    heuristic_has_motion = motion_score >= 0.02

    gemini_result: Dict[str, Any] = {"used": False}
    if use_gemini:
        ok, res = _gemini_check(frames, kling_prompt or description)
        gemini_result = {"used": ok, **res}

    result: Dict[str, Any] = {
        "inputs": {
            "video_path": video_path,
            "original_image_path": original_image_path,
            "description": description,
            "kling_prompt": kling_prompt,
            "generation_seconds": generation_seconds,
        },
        "heuristic": {
            "frame_indices": indices,
            "diffs": diffs,
            "motion_score": motion_score,
            "has_motion": heuristic_has_motion,
        },
        "gemini": gemini_result,
    }

    # Final decision: prefer Gemini parsed if available
    final_has_motion = heuristic_has_motion
    if gemini_result.get("used") and isinstance(gemini_result.get("parsed"), dict):
        parsed = gemini_result["parsed"]
        if isinstance(parsed.get("has_motion"), bool):
            final_has_motion = bool(parsed["has_motion"])
    result["final"] = {"has_motion": final_has_motion}
    return result


def _combine_side_by_side(img_left: Image.Image, img_right: Image.Image, size: int = 512) -> Image.Image:
    left = img_left.convert("RGB").resize((size, size))
    right = img_right.convert("RGB").resize((size, size))
    combined = Image.new("RGB", (size * 2, size))
    combined.paste(left, (0, 0))
    combined.paste(right, (size, 0))
    return combined


def _build_frame_gemini_prompt(original_prompt: str, movement: Dict[str, Any], kling_prompt: str) -> str:
    movement_str = json.dumps(movement, ensure_ascii=False)
    return (
        "Evaluate if RIGHT frame belongs to the SAME WORLD as LEFT original image.\n"
        "Original description: \"" + original_prompt + "\"\n"
        "Camera movement context (JSON): " + movement_str + "\n"
        "Full video prompt used: \"" + kling_prompt + "\"\n\n"
        "Respond with ONLY strict JSON:\n"
        "{\n"
        "  \"consistent\": true/false,\n"
        "  \"confidence\": 0.0-1.0,\n"
        "  \"reasoning\": \"brief\"\n"
        "}"
    )


def classify_frame_consistency(
    original_image_path: str,
    frame_path: str,
    original_description: str,
    movement: Dict[str, Any],
    kling_prompt: str,
    use_gemini: bool = True,
    source_video_path: Optional[str] = None,
) -> Dict[str, Any]:
    # Load images
    left = Image.open(original_image_path).convert("RGB")
    right = Image.open(frame_path).convert("RGB")

    # Heuristic similarity (1 - diff)
    diff = _pil_diff_score(left, right)
    similarity = float(max(0.0, min(1.0, 1.0 - diff)))

    gemini_result: Dict[str, Any] = {"used": False}
    if use_gemini:
        strip = _combine_side_by_side(left, right)
        prompt = _build_frame_gemini_prompt(original_description, movement, kling_prompt)
        if GEMINI_AVAILABLE and os.getenv("GEMINI_API_KEY"):
            try:
                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                model = genai.GenerativeModel("gemini-2.0-flash-exp")
                try:
                    response = model.generate_content([prompt, strip])
                except Exception:
                    buf = io.BytesIO()
                    strip.save(buf, format="JPEG")
                    buf.seek(0)
                    response = model.generate_content([prompt, buf.getvalue()])

                text = getattr(response, "text", "") or ""
                raw = text.strip()
                clean = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
                parsed = None
                try:
                    parsed = json.loads(clean)
                except Exception:
                    try:
                        m = re.search(r"\{[\s\S]*\}", clean)
                        if m:
                            parsed = json.loads(m.group(0))
                    except Exception:
                        parsed = None
                gemini_result = {"used": True, "prompt": prompt, "response_text": raw, "parsed": parsed}
            except Exception as e:
                gemini_result = {"used": False, "error": str(e), "prompt": prompt}
        else:
            gemini_result = {"used": False, "prompt": prompt, "error": "Gemini not configured"}

    # Simple decision rule
    label = "good"
    reason = "heuristic"
    if use_gemini and gemini_result.get("used") and isinstance(gemini_result.get("parsed"), dict):
        parsed = gemini_result["parsed"]
        cons = parsed.get("consistent")
        conf = float(parsed.get("confidence", 0.0)) if isinstance(parsed.get("confidence"), (int, float)) else 0.0
        if isinstance(cons, bool):
            label = "good" if cons else "bad"
            reason = f"gemini:{conf:.2f}"
        else:
            label = "good" if similarity >= 0.7 else "bad"
            reason = "heuristic_fallback_gemini_unparsed"
    else:
        label = "good" if similarity >= 0.7 else "bad"
        reason = "heuristic_only"

    return {
        "inputs": {
            "original_image_path": os.path.abspath(original_image_path),
            "frame_path": os.path.abspath(frame_path),
            "source_video_path": os.path.abspath(source_video_path) if source_video_path else None,
            "description": original_description,
            "movement": movement,
            "kling_prompt": kling_prompt,
        },
        "heuristic": {
            "similarity": similarity
        },
        "gemini": gemini_result,
        "classification": {
            "label": label,
            "reason": reason
        }
    }
