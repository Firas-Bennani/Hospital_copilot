"""
Label Harmonization
===================
Converts source-dataset YOLO label lines to the canonical class set
(`configs/datasets.yaml`). Supports plain bounding-box labels
(`yolov8_detect`) and polygon/segmentation labels (`yolov8_segment`),
which are reduced to their enclosing bounding box.

This module was missing from the shared repository (its directory was
swallowed by the `datasets/` gitignore rule); it is reconstructed from the
behaviour exercised by `tests/test_core.py`.
"""

from __future__ import annotations

from typing import Any


def polygon_to_bbox(values: list[float]) -> tuple[float, float, float, float]:
    """
    Convert a flat list of normalized polygon coordinates
    [x1, y1, x2, y2, ...] to a YOLO bbox (x_center, y_center, w, h).
    """
    xs = values[0::2]
    ys = values[1::2]
    if not xs or not ys:
        return 0.0, 0.0, 0.0, 0.0
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    return (x_min + x_max) / 2.0, (y_min + y_max) / 2.0, x_max - x_min, y_max - y_min


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def harmonize_label_line(
    line: str,
    remap: dict[int, dict[str, Any]],
    source_format: str = "yolov8_detect",
) -> tuple[str | None, dict[str, Any]]:
    """
    Harmonize one YOLO label line.

    Args:
        line: Raw label line (`cls x y w h` or `cls x1 y1 x2 y2 ...`).
        remap: `{source_class_id: {action, canonical_class, canonical_class_id, reason}}`.
        source_format: `yolov8_detect` or `yolov8_segment`.

    Returns:
        (harmonized_line_or_None, info). `info["action"]` is one of
        `REMAP`, `KEEP`, `EXCLUDE`, `UNMAPPED`, `MALFORMED`.
    """
    parts = line.strip().split()
    if len(parts) < 5:
        return None, {"action": "MALFORMED", "reason": "too few fields", "line": line}

    try:
        src_cls = int(float(parts[0]))
        values = [float(v) for v in parts[1:]]
    except ValueError:
        return None, {"action": "MALFORMED", "reason": "non-numeric field", "line": line}

    rule = remap.get(src_cls)
    if rule is None:
        return None, {"action": "UNMAPPED", "source_class_id": src_cls, "line": line}

    action = str(rule.get("action", "REMAP")).upper()
    info: dict[str, Any] = {
        "action": action,
        "source_class_id": src_cls,
        "canonical_class": rule.get("canonical_class"),
        "canonical_class_id": rule.get("canonical_class_id"),
        "reason": rule.get("reason", ""),
    }
    if action == "EXCLUDE" or rule.get("canonical_class_id") is None:
        info["action"] = "EXCLUDE"
        return None, info

    if source_format == "yolov8_segment" or len(values) > 4:
        if len(values) % 2 != 0 or len(values) < 6:
            return None, {"action": "MALFORMED", "reason": "odd polygon length", "line": line}
        x_c, y_c, w, h = polygon_to_bbox(values)
    else:
        x_c, y_c, w, h = values[:4]

    x_c, y_c, w, h = (_clamp01(x_c), _clamp01(y_c), _clamp01(w), _clamp01(h))
    if w <= 0 or h <= 0:
        return None, {"action": "MALFORMED", "reason": "empty box", "line": line}

    out = f"{int(rule['canonical_class_id'])} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}"
    return out, info


def build_remap(class_mapping: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Turn the `class_mapping.<dataset>` list of datasets.yaml into a remap dict."""
    remap: dict[int, dict[str, Any]] = {}
    for entry in class_mapping:
        sid = entry.get("source_class_id")
        if sid is None:
            continue
        remap[int(sid)] = {
            "action": entry.get("action", "REMAP"),
            "canonical_class": entry.get("canonical_class"),
            "canonical_class_id": entry.get("canonical_class_id"),
            "reason": entry.get("reason", ""),
        }
    return remap
