import json
from pathlib import Path

ROOT = Path(__file__).parents[2]
SEED = ROOT / "knowledge" / "seed"


def _rows(name: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (SEED / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_seed_jsonl_is_valid_and_ids_are_unique() -> None:
    for name, key in (
        ("concepts.jsonl", "id"),
        ("error_patterns.jsonl", "code"),
        ("sample_problems.jsonl", "id"),
        ("solution_patterns.jsonl", "id"),
    ):
        values = [row[key] for row in _rows(name)]
        assert len(values) == len(set(values)), f"duplicate {key} in {name}"


def test_benchmark_covers_all_core_chapters() -> None:
    benchmark = [
        json.loads(line)
        for line in (ROOT / "evals" / "datasets" / "benchmark.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    chapters = {row["chapter"] for row in benchmark}
    assert chapters >= {
        "signals",
        "lti",
        "fourier_series",
        "fourier_transform",
        "laplace",
        "z_transform",
        "sampling",
        "system_properties",
    }
    assert len(benchmark) >= 30
