import numpy as np
import pytest

from pitchsight.geometry.offside import PositionInput, homography, position, project


@pytest.mark.parametrize(
    "attacker,ball,opponents,direction,expected",
    [
        (40, 30, [90, 35], 1, "NOT IN OFFSIDE POSITION"),
        (70, 50, [100, 70], 1, "NOT IN OFFSIDE POSITION"),
        (80, 60, [100, 70], 1, "OFFSIDE POSITION"),
        (25, 45, [5, 35], -1, "OFFSIDE POSITION"),
        (80, 85, [100, 70], 1, "NOT IN OFFSIDE POSITION"),
        (52.5, 40, [30, 20], 1, "NOT IN OFFSIDE POSITION"),
    ],
)
def test_law11_position(attacker, ball, opponents, direction, expected):
    assert (
        position(
            PositionInput(
                attacker=attacker,
                ball=ball,
                opponents=opponents,
                direction=direction,
                uncertainty=0,
            )
        )["status"]
        == expected
    )


def test_uncertainty():
    result = position(PositionInput(attacker=70.1, ball=40, opponents=[100, 70], uncertainty=0.2))
    assert result["status"] == "INCONCLUSIVE"
    assert result["offence"] == "NOT DETERMINED"


def test_projection_and_degeneracy():
    source = [[0, 0], [100, 0], [100, 100], [0, 100]]
    target = [[0, 0], [105, 0], [105, 68], [0, 68]]
    result = homography(source, target)
    assert result["reprojection_rmse_metres"] < 1e-6
    assert np.allclose(project([[50, 50]], result["matrix"]), [[52.5, 34]])
    with pytest.raises(ValueError, match="collinear"):
        homography([[0, 0], [1, 1], [2, 2], [3, 3]], target)
    with pytest.raises(ValueError, match="infinity"):
        project([[0, 0]], [[1, 0, 0], [0, 1, 0], [0, 0, 0]])
