import numpy as np
import pytest

from animlib.geometry import Path, align, bezier, morph, shapes


class TestBezier:
    def test_evaluate_hits_endpoints(self) -> None:
        curve = np.array([[0, 0], [1, 2], [3, 2], [4, 0]], dtype=float)
        assert np.allclose(bezier.evaluate(curve, 0.0), [0, 0])
        assert np.allclose(bezier.evaluate(curve, 1.0), [4, 0])

    def test_split_halves_trace_the_same_curve(self) -> None:
        curve = np.array([[0, 0], [1, 2], [3, 2], [4, 0]], dtype=float)
        left, right = bezier.split(curve, 0.3)
        assert np.allclose(bezier.evaluate(left, 0.5), bezier.evaluate(curve, 0.15))
        assert np.allclose(bezier.evaluate(right, 0.5), bezier.evaluate(curve, 0.65))

    def test_subdivide_is_continuous_and_equal_in_parameter(self) -> None:
        curve = np.array([[0, 0], [1, 2], [3, 2], [4, 0]], dtype=float)
        pieces = bezier.subdivide(curve, 4)
        assert pieces.shape == (4, 4, 2)
        assert np.allclose(pieces[1:, 0], pieces[:-1, 3])
        for k, piece in enumerate(pieces):
            assert np.allclose(piece[0], bezier.evaluate(curve, k / 4))

    def test_arc_stays_on_the_circle(self) -> None:
        curves = bezier.arc(0.0, 2 * np.pi, radius=2.0)
        ts = np.linspace(0, 1, 50)
        pts = np.concatenate([bezier.evaluate(c, ts) for c in curves])
        radii = np.linalg.norm(pts, axis=1)
        assert np.allclose(radii, 2.0, rtol=5e-4)

    def test_quadratic_elevation_is_exact(self) -> None:
        p0, c, p1 = np.array([0.0, 0.0]), np.array([1.0, 2.0]), np.array([2.0, 0.0])
        cubic = bezier.quadratic_to_cubic(p0, c, p1)
        for t in (0.2, 0.5, 0.9):
            quad = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * c + t**2 * p1
            assert np.allclose(bezier.evaluate(cubic, t), quad)


class TestPath:
    def test_layout_is_validated(self) -> None:
        curves = np.zeros((2, 4, 2))
        with pytest.raises(ValueError):
            Path(curves, np.array([0, 2]), np.array([True, True]))
        with pytest.raises(ValueError):
            Path(curves, np.array([0, 1]), np.array([True]))

    def test_paths_are_immutable(self) -> None:
        p = shapes.circle()
        with pytest.raises(ValueError):
            p.curves[0, 0, 0] = 10.0

    def test_from_subpaths_round_trips(self) -> None:
        a, b = shapes.circle(), shapes.square()
        both = Path.concat([a, b])
        assert both.num_subpaths == 2
        subs = list(both.subpaths())
        assert np.allclose(subs[0][0], a.curves)
        assert np.allclose(subs[1][0], b.curves)

    def test_transforms(self) -> None:
        sq = shapes.square(2.0)
        assert np.allclose(sq.center(), [0, 0])
        assert np.allclose(sq.shift(3, -1).center(), [3, -1])
        assert sq.scale(2.0).width == pytest.approx(4.0)
        rotated = sq.rotate(np.pi / 4)
        assert rotated.width == pytest.approx(2 * np.sqrt(2))
        assert np.allclose(sq.move_to(1, 1).center(), [1, 1])

    def test_reversed_traces_backwards(self) -> None:
        sq = shapes.square()
        rev = sq.reversed()
        assert np.allclose(rev.curves[0, 0], sq.curves[-1, 3])
        assert np.allclose(rev.reversed().curves, sq.curves)

    def test_shapes_are_counter_clockwise(self) -> None:
        for shape in (shapes.circle(), shapes.square(), shapes.regular_polygon(6), shapes.star()):
            anchors = shape.curves[:, 0]
            x, y = anchors[:, 0], anchors[:, 1]
            signed_area = 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)
            assert signed_area > 0, shape


class TestAlign:
    def test_aligned_paths_share_layout(self) -> None:
        a, b = align(shapes.circle(), shapes.star(7))
        assert a.curves.shape == b.curves.shape
        assert np.array_equal(a.subpath_ids, b.subpath_ids)

    def test_alignment_does_not_change_the_shape(self) -> None:
        star = shapes.star(5)
        _, aligned = align(shapes.circle(), star)
        # Every original corner is still a point on the aligned path
        corners = star.curves[:, 0]
        anchors = aligned.curves[:, 0]
        for corner in corners:
            assert np.min(np.linalg.norm(anchors - corner, axis=1)) < 1e-9

    def test_unmatched_subpaths_grow_from_their_own_centre(self) -> None:
        one = shapes.circle()
        two = Path.concat([shapes.circle(), shapes.circle(0.5).shift(3, 0)])
        start, end = align(one, two)
        assert start.num_subpaths == end.num_subpaths == 2
        second_start = list(start.subpaths())[1][0]
        assert np.allclose(second_start.reshape(-1, 2), [3, 0])

    def test_morph_endpoints_and_midpoint(self) -> None:
        m = morph(shapes.circle(1.0), shapes.square(2.0))
        assert np.allclose(m.at(0.0).curves, m.start.curves)
        assert np.allclose(m.at(1.0).curves, m.end.curves)
        mid = m.at(0.5).curves
        assert np.allclose(mid, (m.start.curves + m.end.curves) / 2)

    def test_circle_to_square_does_not_twist(self) -> None:
        # The circle's rightmost point should travel to the square's right edge midpoint,
        # not to a corner, which would turn the shape 45 degrees on the way
        m = morph(shapes.circle(1.0), shapes.square(2.0))
        i = int(np.argmin(np.linalg.norm(m.start.curves[:, 0] - [1.0, 0.0], axis=1)))
        assert np.allclose(m.end.curves[i, 0], [1.0, 0.0])
