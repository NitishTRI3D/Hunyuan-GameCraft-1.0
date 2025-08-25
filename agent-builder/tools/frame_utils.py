from __future__ import annotations
import os
from typing import List

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None  # type: ignore


def extract_frames(video_path: str, output_dir: str, max_frames: int = 12) -> List[str]:
    if cv2 is None:
        raise RuntimeError("OpenCV is required for frame extraction but is not installed.")
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {video_path}")

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total <= 0:
        # Fallback: sequential read
        paths: List[str] = []
        idx = 0
        while idx < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            out_path = os.path.join(output_dir, f"frame_{idx:04d}.jpg")
            cv2.imwrite(out_path, frame)
            paths.append(out_path)
            idx += 1
        cap.release()
        return paths

    step = max(1, total // max_frames) if max_frames > 0 else 1
    indices = list(range(0, total, step))[:max_frames]

    out_paths: List[str] = []
    for i, idx in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, frame = cap.read()
        if not ok:
            continue
        out_path = os.path.join(output_dir, f"frame_{i:04d}.jpg")
        cv2.imwrite(out_path, frame)
        out_paths.append(out_path)
    cap.release()
    return out_paths


def extract_start_frame(video_path: str, output_image_path: str) -> bool:
    """
    Save the first frame of the video to output_image_path (JPEG). Returns True on success.
    """
    if cv2 is None:
        return False
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return False
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return False
    os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
    try:
        return bool(cv2.imwrite(output_image_path, frame))
    except Exception:
        return False


