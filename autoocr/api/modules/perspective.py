"""Perspective (keystone) correction module.

Detection:
  - Finds the largest 4-point contour approximating the document boundary.
  - Computes its area ratio vs image area and checks if it's sufficiently convex & not axis-aligned.
  - If quadrilateral differs from axis-aligned rectangle beyond a tolerance, triggers correction.

Processing:
  - Orders corner points (top-left, top-right, bottom-right, bottom-left).
  - Applies a four-point perspective warp to produce a flattened bird's-eye view.

Notes:
  - Runs after orientation, before deskew ideally (but we place it before deskew in pipeline if added there).
  - Avoids applying if distortion minimal (aspect difference < threshold).
"""
from __future__ import annotations
from typing import Tuple, Dict, Any
import cv2
import numpy as np

from .base_module import BaseModule


class PerspectiveModule(BaseModule):
    name = "perspective"

    def __init__(self, min_area_ratio: float = 0.5, skew_tolerance: float = 0.015):
        self.min_area_ratio = min_area_ratio
        self.skew_tolerance = skew_tolerance

    def detect(self, image) -> Tuple[bool, Dict[str, Any]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return False, {"reason": "no_contours"}
        largest = max(contours, key=cv2.contourArea)
        peri = cv2.arcLength(largest, True)
        approx = cv2.approxPolyDP(largest, 0.02 * peri, True)
        h, w = gray.shape
        image_area = h * w
        area = float(cv2.contourArea(largest))
        area_ratio = area / image_area if image_area else 0.0
        if len(approx) != 4 or area_ratio < self.min_area_ratio:
            return False, {"reason": "not_quad_or_small", "area_ratio": area_ratio}
        # Check if near axis-aligned rectangle by comparing polygon area vs its bounding box area
        x, y, bw, bh = cv2.boundingRect(approx)
        box_area = bw * bh
        if box_area == 0:
            return False, {"reason": "zero_box"}
        fill_ratio = area / box_area
        # If fill ratio ~1, it's already near axis-aligned; skip
        needs = fill_ratio < (1 - self.skew_tolerance)
        return needs, {"area_ratio": area_ratio, "fill_ratio": fill_ratio, "approx": approx.reshape(-1, 2).tolist()}

    def process(self, image, detect_meta: Dict[str, Any]):
        pts = detect_meta.get("approx")
        if not pts:
            return image, {"applied": False}
        pts = np.array(pts, dtype="float32")
        # Order points
        rect = self._order_points(pts)
        (tl, tr, br, bl) = rect
        widthA = np.linalg.norm(br - bl)
        widthB = np.linalg.norm(tr - tl)
        maxWidth = int(max(widthA, widthB))
        heightA = np.linalg.norm(tr - br)
        heightB = np.linalg.norm(tl - bl)
        maxHeight = int(max(heightA, heightB))
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]
        ], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight), flags=cv2.INTER_CUBIC)
        return warped, {"applied": True, "output_size": [maxWidth, maxHeight]}

    @staticmethod
    def _order_points(pts: np.ndarray) -> np.ndarray:
        # Orders 4 points: tl, tr, br, bl
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # tl
        rect[2] = pts[np.argmax(s)]  # br
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # tr
        rect[3] = pts[np.argmax(diff)]  # bl
        return rect

__all__ = ["PerspectiveModule"]
