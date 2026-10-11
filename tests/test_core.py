import numpy as np
import pytest

from animlib.core import Color, easing


class TestEasing:
    @pytest.mark.parametrize("name", ["linear", "smooth", "ease_in", "ease_out", "overshoot"])
    def test_fixes_endpoints(self, name: str) -> None:
        f = easing.EASINGS[name]
        assert f(0.0) == pytest.approx(0.0)
        assert f(1.0) == pytest.approx(1.0)

    def test_smooth_is_flat_at_both_ends(self) -> None:
        h = 1e-4
        assert easing.smooth(h) / h == pytest.approx(0.0, abs=1e-3)
        assert (1 - easing.smooth(1 - h)) / h == pytest.approx(0.0, abs=1e-3)

    def test_works_on_arrays(self) -> None:
        t = np.linspace(0, 1, 11)
        assert np.all(np.diff(easing.smooth(t)) >= 0)
        assert easing.there_and_back(t)[5] == pytest.approx(1.0)
        assert easing.there_and_back(t)[-1] == pytest.approx(0.0)

    def test_overshoot_goes_past_one(self) -> None:
        assert max(easing.overshoot(t) for t in np.linspace(0, 1, 101)) > 1.0

    def test_lagged_staggers_starts(self) -> None:
        # With lag 1, part 1 of 2 has not started at the halfway mark and finishes at the end
        assert easing.lagged(0.5, 1, 2, lag_ratio=1.0) == pytest.approx(0.0)
        assert easing.lagged(1.0, 1, 2, lag_ratio=1.0) == pytest.approx(1.0)
        # With lag 0 every part runs together
        assert easing.lagged(0.4, 3, 5, lag_ratio=0.0) == pytest.approx(0.4)


class TestColor:
    def test_parses_hex_forms(self) -> None:
        assert Color.parse("#fff") == Color(1, 1, 1)
        assert Color.parse("#58C4DD").to_hex() == "#58C4DD"
        assert Color.parse("#00000080").a == pytest.approx(128 / 255)

    def test_rejects_bad_input(self) -> None:
        with pytest.raises(ValueError):
            Color.parse("#12")
        with pytest.raises(ValueError):
            Color.parse("#zzzzzz")
        with pytest.raises(ValueError):
            Color(1.2, 0, 0)

    def test_lerp_clamps_overshoot(self) -> None:
        black, white = Color(0, 0, 0), Color(1, 1, 1)
        assert black.lerp(white, 0.5) == Color(0.5, 0.5, 0.5)
        assert black.lerp(white, 1.3) == white
