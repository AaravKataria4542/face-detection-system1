"""
Unit tests for the face detection service.
These tests use synthetic images so no camera is required.
MediaPipe is mocked where needed to keep tests fast and deterministic.
"""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from app.services.face_detection import (
    DetectionResult,
    FaceDetector,
    _draw_roi_pillow,
    process_frame,
)


def _make_jpeg(width: int = 320, height: int = 240) -> bytes:
    """Create a solid-colour JPEG in memory."""
    img = Image.new("RGB", (width, height), color=(120, 80, 60))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# DetectionResult
# ---------------------------------------------------------------------------

class TestDetectionResult:
    def test_defaults_no_face(self):
        det = DetectionResult(found=False)
        assert det.found is False
        assert det.confidence == 0.0

    def test_face_coords(self):
        det = DetectionResult(
            found=True,
            x_norm=0.1, y_norm=0.2, width_norm=0.3, height_norm=0.4,
            x_px=32, y_px=48, width_px=96, height_px=96,
            confidence=0.95,
            frame_width=320, frame_height=240,
        )
        assert det.x_px == 32
        assert det.confidence == pytest.approx(0.95)


# ---------------------------------------------------------------------------
# _draw_roi_pillow
# ---------------------------------------------------------------------------

class TestDrawROIPillow:
    def test_returns_pil_image(self):
        img = Image.new("RGB", (320, 240), color=(200, 200, 200))
        det = DetectionResult(
            found=True,
            x_px=50, y_px=50, width_px=100, height_px=100,
            confidence=0.9, frame_width=320, frame_height=240,
        )
        result = _draw_roi_pillow(img, det, color=(0, 255, 0), thickness=2)
        assert isinstance(result, Image.Image)
        assert result.size == (320, 240)

    def test_draws_green_pixels_on_border(self):
        img = Image.new("RGB", (320, 240), color=(0, 0, 0))
        det = DetectionResult(
            found=True,
            x_px=10, y_px=10, width_px=100, height_px=80,
            confidence=0.9, frame_width=320, frame_height=240,
        )
        result = _draw_roi_pillow(img, det, color=(0, 255, 0), thickness=1)
        # Top-left corner pixel on the rectangle should be green-ish
        pixel = result.getpixel((10, 10))
        assert pixel[1] > 200, "Expected green channel to be high on ROI border"


# ---------------------------------------------------------------------------
# FaceDetector (mocked MediaPipe)
# ---------------------------------------------------------------------------

class TestFaceDetector:
    def _mock_detection(self, xmin, ymin, w, h, score=0.92):
        det = MagicMock()
        det.location_data.relative_bounding_box.xmin = xmin
        det.location_data.relative_bounding_box.ymin = ymin
        det.location_data.relative_bounding_box.width = w
        det.location_data.relative_bounding_box.height = h
        det.score = [score]
        return det

    @patch("app.services.face_detection.mp_face_detection.FaceDetection")
    def test_detect_face_found(self, MockFD):
        mock_fd_instance = MockFD.return_value
        mock_fd_instance.process.return_value = MagicMock(
            detections=[self._mock_detection(0.1, 0.2, 0.3, 0.4)]
        )
        detector = FaceDetector()
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        result = detector.detect(frame)

        assert result.found is True
        assert result.confidence == pytest.approx(0.92)
        assert result.x_px == int(0.1 * 320)
        assert result.y_px == int(0.2 * 240)

    @patch("app.services.face_detection.mp_face_detection.FaceDetection")
    def test_detect_no_face(self, MockFD):
        mock_fd_instance = MockFD.return_value
        mock_fd_instance.process.return_value = MagicMock(detections=[])
        detector = FaceDetector()
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        result = detector.detect(frame)

        assert result.found is False

    @patch("app.services.face_detection.mp_face_detection.FaceDetection")
    def test_clamps_negative_xmin(self, MockFD):
        mock_fd_instance = MockFD.return_value
        mock_fd_instance.process.return_value = MagicMock(
            detections=[self._mock_detection(-0.05, 0.0, 0.5, 0.5)]
        )
        detector = FaceDetector()
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        result = detector.detect(frame)
        assert result.x_norm >= 0.0


# ---------------------------------------------------------------------------
# process_frame integration (mocked detector)
# ---------------------------------------------------------------------------

class TestProcessFrame:
    @patch("app.services.face_detection.mp_face_detection.FaceDetection")
    def test_returns_bytes_and_result(self, MockFD):
        mock_fd_instance = MockFD.return_value
        mock_det = MagicMock()
        mock_det.location_data.relative_bounding_box.xmin = 0.1
        mock_det.location_data.relative_bounding_box.ymin = 0.1
        mock_det.location_data.relative_bounding_box.width = 0.3
        mock_det.location_data.relative_bounding_box.height = 0.4
        mock_det.score = [0.88]
        mock_fd_instance.process.return_value = MagicMock(detections=[mock_det])

        detector = FaceDetector()
        jpeg = _make_jpeg()
        annotated, det = process_frame(jpeg, detector)

        assert isinstance(annotated, bytes)
        assert len(annotated) > 0
        assert det is not None
        assert det.found is True

    @patch("app.services.face_detection.mp_face_detection.FaceDetection")
    def test_no_face_returns_none_det(self, MockFD):
        mock_fd_instance = MockFD.return_value
        mock_fd_instance.process.return_value = MagicMock(detections=[])

        detector = FaceDetector()
        jpeg = _make_jpeg()
        annotated, det = process_frame(jpeg, detector)

        assert det is None
        assert isinstance(annotated, bytes)

    def test_invalid_bytes_returns_original(self):
        detector = FaceDetector.__new__(FaceDetector)
        detector._detector = MagicMock()
        garbage = b"not a valid image"
        result_bytes, det = process_frame(garbage, detector)
        assert result_bytes == garbage
        assert det is None
