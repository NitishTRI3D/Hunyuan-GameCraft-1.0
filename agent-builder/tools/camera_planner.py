from __future__ import annotations
import random
from typing import Dict, List, Optional


INDOOR_MOVES: List[Dict] = [
    {"type": "dolly_in", "intensity": "high", "description": "fast dolly forward 1-2 meters, subtle parallax"},
    {"type": "dolly_out", "intensity": "slow", "description": "slow dolly backward, maintain composition"},
    {"type": "truck_left", "intensity": "slow", "description": "lateral move left with gentle parallax"},
    {"type": "truck_right", "intensity": "slow", "description": "lateral move right with gentle parallax"},
    {"type": "pan_left", "intensity": "high", "description": "Move camera towards right, 360 degree to come back to same position. No humans in the office. No moving objects as the camera is panning. Still Office."},
    {"type": "pan_right", "intensity": "slow", "description": "slow pan right, keep horizon stable"},
    {"type": "orbit_small", "intensity": "slow", "description": "small 90° orbit around center of scene"},
    {"type": "zoom_in", "intensity": "gentle", "description": "gentle optical zoom in, no exposure change"},
    {"type": "zoom_out", "intensity": "gentle", "description": "gentle optical zoom out, no exposure change"},
    {"type": "pedestal_up", "intensity": "fast", "description": "slow crane up by 1-2meter, keep framing centered"},
]

OUTDOOR_MOVES: List[Dict] = [
    {"type": "orbit_360", "intensity": "slow", "description": "slow 360° orbit around central subject"},
    {"type": "arc_left", "intensity": "slow", "description": "slow left arc, maintain equal distance"},
    {"type": "arc_right", "intensity": "slow", "description": "slow right arc, maintain equal distance"},
    {"type": "dolly_in", "intensity": "slow", "description": "slow dolly forward 2-3 meters across ground"},
    {"type": "dolly_out", "intensity": "slow", "description": "slow dolly backward 2-3 meters"},
    {"type": "tilt_up", "intensity": "slow", "description": "slow tilt up from ground to skyline"},
    {"type": "tilt_down", "intensity": "slow", "description": "slow tilt down from skyline to ground"},
    {"type": "pan_left", "intensity": "slow", "description": "slow pan left across landscape"},
    {"type": "pan_right", "intensity": "slow", "description": "slow pan right across landscape"},
    {"type": "pedestal_up", "intensity": "slow", "description": "slow crane up 0.5-1m for reveal"},
]


def detect_scene_type(description: str) -> str:
    d = (description or "").lower()
    indoor_keywords = ["room", "office", "indoor", "kitchen", "bedroom", "hall", "studio", "interior", "glass-walled"]
    outdoor_keywords = ["outdoor", "street", "landscape", "mountain", "beach", "city", "forest", "park", "skyline"]
    indoor_score = sum(1 for k in indoor_keywords if k in d)
    outdoor_score = sum(1 for k in outdoor_keywords if k in d)
    if outdoor_score > indoor_score:
        return "outdoor"
    return "indoor"


def propose_movements(description: str, count: int) -> List[Dict]:
    scene_type = detect_scene_type(description)
    pool = OUTDOOR_MOVES if scene_type == "outdoor" else INDOOR_MOVES
    # Sample without replacement if possible; otherwise allow repeats
    if count <= len(pool):
        return random.sample(pool, count)
    moves: List[Dict] = []
    while len(moves) < count:
        moves.extend(random.sample(pool, min(len(pool), count - len(moves))))
    return moves


def build_kling_prompt(description: str, movement: Dict) -> str:
    base = (description or "").strip()
    if base and not base.endswith("."):
        base += "."
    safety = " No humans in the video. No moving objects in the video."
    move_text = movement.get("description") or movement.get("type", "slow camera move")
    # Normalize phrasing for Kling
    move_clause = f" Camera: {move_text}. Return to original composition at end."
    return (base + move_clause + safety).strip()


