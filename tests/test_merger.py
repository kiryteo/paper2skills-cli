"""Tests for cosine similarity and merge group building."""

import math

from paper2skills.evaluate.merger import (
    _cosine_similarity,
    _build_merge_groups,
    OverlapPair,
)


# ---------------------------------------------------------------------------
# _cosine_similarity
# ---------------------------------------------------------------------------


class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert math.isclose(_cosine_similarity(v, v), 1.0, rel_tol=1e-9)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert math.isclose(_cosine_similarity(a, b), 0.0, abs_tol=1e-9)

    def test_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert math.isclose(_cosine_similarity(a, b), -1.0, rel_tol=1e-9)

    def test_zero_vector_returns_zero(self):
        a = [0.0, 0.0, 0.0]
        b = [1.0, 2.0, 3.0]
        assert _cosine_similarity(a, b) == 0.0
        assert _cosine_similarity(b, a) == 0.0

    def test_both_zero_returns_zero(self):
        a = [0.0, 0.0]
        b = [0.0, 0.0]
        assert _cosine_similarity(a, b) == 0.0

    def test_known_value(self):
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        # dot=32, |a|=sqrt(14), |b|=sqrt(77)
        expected = 32.0 / (math.sqrt(14) * math.sqrt(77))
        assert math.isclose(_cosine_similarity(a, b), expected, rel_tol=1e-9)

    def test_single_dimension(self):
        assert math.isclose(_cosine_similarity([3.0], [5.0]), 1.0, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# _build_merge_groups (union-find)
# ---------------------------------------------------------------------------


class TestBuildMergeGroups:
    def _pair(self, a, b, should_merge=True, score=0.9):
        return OverlapPair(
            skill_a=a,
            skill_b=b,
            overlap_score=score,
            should_merge=should_merge,
            reason="test",
        )

    def test_no_merge_pairs(self):
        pairs = [self._pair("a", "b", should_merge=False)]
        assert _build_merge_groups(pairs) == []

    def test_single_merge_pair(self):
        pairs = [self._pair("a", "b")]
        groups = _build_merge_groups(pairs)
        assert len(groups) == 1
        assert sorted(groups[0]) == ["a", "b"]

    def test_two_separate_groups(self):
        pairs = [
            self._pair("a", "b"),
            self._pair("c", "d"),
        ]
        groups = _build_merge_groups(pairs)
        assert len(groups) == 2
        group_sets = [set(g) for g in groups]
        assert {"a", "b"} in group_sets
        assert {"c", "d"} in group_sets

    def test_transitive_merge(self):
        """a-b and b-c should produce one group {a, b, c}."""
        pairs = [
            self._pair("a", "b"),
            self._pair("b", "c"),
        ]
        groups = _build_merge_groups(pairs)
        assert len(groups) == 1
        assert sorted(groups[0]) == ["a", "b", "c"]

    def test_mixed_merge_and_no_merge(self):
        pairs = [
            self._pair("a", "b", should_merge=True),
            self._pair("a", "c", should_merge=False),
            self._pair("d", "e", should_merge=True),
        ]
        groups = _build_merge_groups(pairs)
        assert len(groups) == 2
        group_sets = [set(g) for g in groups]
        assert {"a", "b"} in group_sets
        assert {"d", "e"} in group_sets

    def test_empty_pairs(self):
        assert _build_merge_groups([]) == []

    def test_chain_of_four(self):
        """a-b, b-c, c-d should produce one group."""
        pairs = [
            self._pair("a", "b"),
            self._pair("b", "c"),
            self._pair("c", "d"),
        ]
        groups = _build_merge_groups(pairs)
        assert len(groups) == 1
        assert sorted(groups[0]) == ["a", "b", "c", "d"]
