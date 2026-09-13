#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RapidOCR 适配层：用 ONNX 模型替代本机 Tesseract。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Union

import numpy as np
from PIL import Image

try:
    from rapidocr import RapidOCR

    HAS_RAPIDOCR = True
except ImportError:
    RapidOCR = None  # type: ignore
    HAS_RAPIDOCR = False

_ENGINE = None


def require_engine():
    """返回进程内复用的 RapidOCR 引擎。"""
    if not HAS_RAPIDOCR:
        raise ImportError(
            "rapidocr 未安装。请用当前 Python 执行: pip install rapidocr"
        )
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = RapidOCR()
    return _ENGINE


def _as_input(image: Union[str, Path, Image.Image, np.ndarray]):
    if isinstance(image, (str, Path)):
        return str(image)
    if isinstance(image, Image.Image):
        return np.array(image.convert("RGB"))
    if isinstance(image, np.ndarray):
        return image
    raise TypeError(f"不支持的图像类型: {type(image)}")


def _box_xywh(box) -> tuple[int, int, int, int]:
    pts = np.asarray(box, dtype=float).reshape(-1, 2)
    left = int(max(0, round(pts[:, 0].min())))
    top = int(max(0, round(pts[:, 1].min())))
    right = int(round(pts[:, 0].max()))
    bottom = int(round(pts[:, 1].max()))
    return left, top, max(1, right - left), max(1, bottom - top)


def recognize(image: Union[str, Path, Image.Image, np.ndarray]) -> List[Dict[str, Any]]:
    """识别一行结果：按阅读顺序（上到下、左到右）。"""
    output = require_engine()(_as_input(image))
    txts = tuple(getattr(output, "txts", None) or ())
    boxes = getattr(output, "boxes", None)
    scores = tuple(getattr(output, "scores", None) or ())
    if boxes is None:
        boxes = []
    items: List[Dict[str, Any]] = []
    for idx, text in enumerate(txts):
        stripped = str(text or "").strip()
        if not stripped:
            continue
        box = boxes[idx] if idx < len(boxes) else [[0, 0], [1, 0], [1, 1], [0, 1]]
        left, top, width, height = _box_xywh(box)
        score = float(scores[idx]) if idx < len(scores) else 0.0
        items.append(
            {
                "text": stripped,
                "left": left,
                "top": top,
                "width": width,
                "height": height,
                "conf": int(round(max(0.0, min(1.0, score)) * 100)),
            }
        )
    items.sort(key=lambda item: (item["top"] // 12, item["left"]))
    return items


def image_to_string(image: Union[str, Path, Image.Image, np.ndarray]) -> str:
    items = recognize(image)
    if not items:
        return ""
    lines: List[str] = []
    current_top = items[0]["top"]
    current: List[str] = []
    for item in items:
        if current and abs(item["top"] - current_top) > max(12, item["height"] // 2):
            lines.append(" ".join(current))
            current = [item["text"]]
            current_top = item["top"]
        else:
            current.append(item["text"])
            current_top = min(current_top, item["top"])
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def image_to_data(image: Union[str, Path, Image.Image, np.ndarray]) -> Dict[str, List[Any]]:
    """近似 Tesseract image_to_data 的 DICT，供结构化导出和可检索 PDF 使用。"""
    items = recognize(image)
    data: Dict[str, List[Any]] = {
        "text": [],
        "left": [],
        "top": [],
        "width": [],
        "height": [],
        "conf": [],
        "block_num": [],
        "line_num": [],
        "word_num": [],
    }
    line_num = 0
    word_num = 0
    last_top = None
    for item in items:
        if last_top is None or abs(item["top"] - last_top) > max(12, item["height"] // 2):
            line_num += 1
            word_num = 1
            last_top = item["top"]
        else:
            word_num += 1
        data["text"].append(item["text"])
        data["left"].append(item["left"])
        data["top"].append(item["top"])
        data["width"].append(item["width"])
        data["height"].append(item["height"])
        data["conf"].append(item["conf"])
        data["block_num"].append(1)
        data["line_num"].append(line_num)
        data["word_num"].append(word_num)
    return data
