"""
Face detection service using MediaPipe FaceDetection.
OpenCV is explicitly NOT used anywhere in this codebase.
Drawing is done via Pillow (PIL).
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Optional

import mediapipe as mp
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

mp_face_detection = mp.solutions.face_detection


@dataclass
class DetectionResult:
    found: bool
    x_norm: float = 0.0
    y_norm: float = 0.0
    width_norm: float = 0.0
    height_norm: float = 0.0
    x_px: int = 0
    y_px: int = 0
    width_px: int = 0
    height_px: int = 0
    confidence: float = 0.0
    frame_width: int = 0
    frame_height: int = 0


class FaceDetector:
    """
    Wraps MediaPipe FaceDetection.
    Thread-local instances should be used in production; here we share one
    instance since we serialise frames through a single async loop.
    """

    def __init__(self, min_detection_confidence: float = 0.5) -> None:
        self._detector = mp_face_detection.FaceDetection(
            model_selection=0,  # short-range model (≤2 m)
            min_detection_confidence=min_detection_confidence,
        )

    def detect(self, image_rgb: np.ndarray) -> DetectionResult:
        """
        Run face detection on an H×W×3 uint8 RGB numpy array.
        Returns the first (highest-confidence) detection only.
        """
        h, w = image_rgb.shape[:2]
        results = self._detector.process(image_rgb)

        if not results.detections:
            return DetectionResult(found=False, frame_width=w, frame_height=h)

        detection = results.detections[0]  # single face assumption
        bbox = detection.location_data.relative_bounding_box

        # Clamp normalised coords to [0, 1]
        xn = max(0.0, bbox.xmin)
        yn = max(0.0, bbox.ymin)
        wn = min(1.0 - xn, bbox.width)
        hn = min(1.0 - yn, bbox.height)

        # Convert to pixels
        xp = int(xn * w)
        yp = int(yn * h)
        wp = int(wn * w)
        hp = int(hn * h)

        confidence = detection.score[0] if detection.score else 1.0

        return DetectionResult(
            found=True,
            x_norm=xn,
            y_norm=yn,
            width_norm=wn,
            height_norm=hn,
            x_px=xp,
            y_px=yp,
            width_px=wp,
            height_px=hp,
            confidence=float(confidence),
            frame_width=w,
            frame_height=h,
        )

    def close(self) -> None:
        self._detector.close()


# ---------------------------------------------------------------------------
# ROI drawing helpers – Pillow only, zero OpenCV
# ---------------------------------------------------------------------------

def _draw_roi_pillow(
    pil_img: Image.Image,
    det: DetectionResult,
    color: tuple[int, int, int] = (0, 255, 0),
    thickness: int = 3,
) -> Image.Image:
    """
    Draw an axis-aligned minimal bounding box rectangle on *pil_img* in-place
    and return the mutated image.  No OpenCV used.
    """
    draw = ImageDraw.Draw(pil_img)

    x0, y0 = det.x_px, det.y_px
    x1, y1 = det.x_px + det.width_px, det.y_px + det.height_px

    # Draw multiple concentric rectangles to simulate line thickness
    for offset in range(thickness):
        draw.rectangle(
            [x0 - offset, y0 - offset, x1 + offset, y1 + offset],
            outline=color,
        )

    # Label
    label = f"Face {det.confidence:.0%}"
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except OSError:
        font = ImageFont.load_default()

    # Label background pill
    text_bbox = draw.textbbox((x0, y0 - 20), label, font=font)
    draw.rectangle(text_bbox, fill=color)
    draw.text((x0, y0 - 20), label, fill=(0, 0, 0), font=font)

    return pil_img


def process_frame(
    raw_jpeg: bytes,
    detector: FaceDetector,
) -> tuple[bytes, Optional[DetectionResult]]:
    """
    Decode JPEG bytes → detect face → draw ROI → re-encode JPEG.
    Returns (annotated_jpeg_bytes, DetectionResult | None).
    OpenCV is NOT used.
    """
    try:
        pil_img = Image.open(io.BytesIO(raw_jpeg)).convert("RGB")
    except Exception as exc:
        logger.warning("Failed to decode frame: %s", exc)
        return raw_jpeg, None

    # Resize if too large
    max_w, max_h = settings.MAX_FRAME_WIDTH, settings.MAX_FRAME_HEIGHT
    if pil_img.width > max_w or pil_img.height > max_h:
        pil_img.thumbnail((max_w, max_h), Image.LANCZOS)

    np_frame = np.array(pil_img, dtype=np.uint8)
    det = detector.detect(np_frame)

    if det.found:
        pil_img = _draw_roi_pillow(
            pil_img,
            det,
            color=settings.ROI_COLOR,
            thickness=settings.ROI_THICKNESS,
        )

    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=settings.JPEG_QUALITY)
    return buf.getvalue(), det if det.found else None
