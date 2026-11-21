from pathlib import Path

import numpy as np

from glfm.tools import compute_nearest_languages as compute


class FakeLang2Vec:
    vectors = {
        "aaa": [1, 0],
        "bbb": [0, 1],
        "ccc": [1, 1],
    }

    @classmethod
    def available_languages(cls):
        return list(cls.vectors)

    @classmethod
    def get_features(cls, codes, _distance_type):
        return {code: cls.vectors[code] for code in codes}


def _data():
    return {
        code: {"iso639_3": code, "written": True}
        for code in FakeLang2Vec.vectors
    }


def test_chunked_distance_computation_and_checkpoint_resume(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(compute, "_require_numpy", lambda: np)
    monkeypatch.setattr(compute, "_require_lang2vec", lambda: FakeLang2Vec)
    checkpoint = tmp_path / "nearest.checkpoint.json"

    result = compute.build_nearest_map(
        _data(),
        max_neighbors=2,
        distance_type="syntax_knn",
        decimals=(4, 6),
        checkpoint_interval=1,
        matrix_chunk_size=1,
        checkpoint_path=checkpoint,
    )

    assert result["aaa"][0]["lang"] == "ccc"
    assert result["aaa"][0]["distance"] == 0.5
    assert result["bbb"][0]["lang"] == "ccc"
    assert result["ccc"][0]["lang"] == "aaa"

    monkeypatch.setattr(
        compute,
        "_require_lang2vec",
        lambda: (_ for _ in ()).throw(AssertionError("recomputed")),
    )
    resumed = compute.build_nearest_map(
        _data(),
        max_neighbors=2,
        distance_type="syntax_knn",
        decimals=(4, 6),
        checkpoint_interval=1,
        matrix_chunk_size=1,
        checkpoint_path=checkpoint,
    )
    assert resumed == result
