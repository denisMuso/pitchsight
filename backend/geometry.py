from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from pitchsight.geometry.offside import PositionInput, homography, position, project


class CalibrationInput(BaseModel):
    image_points: list[tuple[float, float]] = Field(min_length=4, max_length=100)
    pitch_points: list[tuple[float, float]] = Field(min_length=4, max_length=100)
    query_points: list[tuple[float, float]] = Field(default_factory=list, max_length=100)


router = APIRouter(prefix="/api/offside")


@router.post("/position")
def check_position(body: PositionInput):
    try:
        return position(body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@router.post("/calibrate")
def calibrate(body: CalibrationInput):
    try:
        result = homography(body.image_points, body.pitch_points)
        if body.query_points:
            result["projected_points"] = project(body.query_points, result["matrix"]).tolist()
        return result
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
