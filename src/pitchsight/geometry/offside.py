"""Position-only planar laboratory, not a Law 11 offence adjudicator."""

from typing import Literal

import cv2
import numpy as np
from pydantic import BaseModel, Field


class PositionInput(BaseModel):
    attacker: float = Field(ge=0, le=105, allow_inf_nan=False)
    ball: float = Field(ge=0, le=105, allow_inf_nan=False)
    opponents: list[float] = Field(min_length=2, max_length=11)
    direction: Literal[1, -1] = 1
    uncertainty: float = Field(default=0.25, ge=0, le=10, allow_inf_nan=False)


def position(body: PositionInput):
    defenders = np.asarray(body.opponents, dtype=float)
    if not np.isfinite(defenders).all() or (defenders < 0).any() or (defenders > 105).any():
        raise ValueError("Opponent coordinates must be finite and within pitch")

    def transform(x):
        return x if body.direction == 1 else 105 - x

    attacker, ball = transform(body.attacker), transform(body.ball)
    opponents = sorted((transform(float(x)) for x in defenders), reverse=True)
    reference = max(ball, opponents[1], 52.5)
    margin = attacker - reference
    # Worst-case bounded x-coordinate error for both attacker and reference.
    spread = 2 * body.uncertainty
    if body.uncertainty > 0 and abs(margin) <= spread:
        status = "INCONCLUSIVE"
    else:
        status = "OFFSIDE POSITION" if margin > 0 else "NOT IN OFFSIDE POSITION"
    return {
        "status": status,
        "reference_x": transform(reference),
        "second_last_x": transform(opponents[1]),
        "margin_metres": margin,
        "margin_interval": [margin - spread, margin + spread],
        "offence": "NOT DETERMINED",
        "research_only": True,
        "explanation": "Position at the relevant teammate touch only. Active involvement, exceptions, body parts, timing and deliberate play require human review.",
    }


def project(points, homography):
    points, h = np.asarray(points, dtype=float), np.asarray(homography, dtype=float)
    if (
        points.ndim != 2
        or points.shape[1] != 2
        or h.shape != (3, 3)
        or not np.isfinite(points).all()
        or not np.isfinite(h).all()
    ):
        raise ValueError("Expected finite Nx2 points and 3x3 homography")
    out = np.column_stack([points, np.ones(len(points))]) @ h.T
    if (np.abs(out[:, 2]) < 1e-9).any():
        raise ValueError("Projection approaches infinity")
    return out[:, :2] / out[:, 2:3]


def homography(image_points, pitch_points):
    source, target = np.asarray(image_points, dtype=float), np.asarray(pitch_points, dtype=float)
    if (
        source.shape != target.shape
        or source.ndim != 2
        or source.shape[1] != 2
        or len(source) < 4
        or len(source) > 100
    ):
        raise ValueError("Provide 4–100 paired image/pitch points")
    for points in (source, target):
        if (
            not np.isfinite(points).all()
            or len(np.unique(points, axis=0)) != len(points)
            or np.linalg.matrix_rank(points - points.mean(axis=0)) < 2
        ):
            raise ValueError("Calibration points are duplicate, collinear, or nonfinite")
    h, _ = cv2.findHomography(source, target, method=0)
    if (
        h is None
        or not np.isfinite(h).all()
        or np.linalg.cond(h) > 1e10
        or abs(np.linalg.det(h)) < 1e-12
    ):
        raise ValueError("Degenerate or ill-conditioned calibration")
    errors = np.linalg.norm(project(source, h) - target, axis=1)
    rmse = float(np.sqrt(np.mean(errors**2)))
    return {
        "matrix": h.tolist(),
        "reprojection_rmse_metres": rmse,
        "max_error_metres": float(errors.max()),
        "warning": "Training-point residual is not real-world accuracy. Four points can fit exactly. Ground-plane homography cannot locate airborne body parts.",
    }
