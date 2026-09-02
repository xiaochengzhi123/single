from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from signaltutor.agents.text_parser import parse_text_problem
from signaltutor.api.dependencies import build_services
from signaltutor.schemas.api import SolveProblemRequest
from signaltutor.workflows.solve_problem import solve_problem


async def run(limit: int | None = None) -> None:
    examples = [
        json.loads(line)
        for line in Path("evals/datasets/benchmark.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    service = build_services()
    passed = 0
    for example in examples[:limit]:
        problem = parse_text_problem(example["question"])
        stored = await service.problems.create(problem)
        result = await solve_problem(SolveProblemRequest(), service.workflow(stored.id, problem))
        chapter_ok = (
            result.classification is not None
            and result.classification.chapter == example["chapter"]
        )
        passed += int(chapter_ok)
        print(f"{example['id']}: {'PASS' if chapter_ok else 'FAIL'}")
    print(f"Chapter classification: {passed}/{min(len(examples), limit or len(examples))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    asyncio.run(run(args.limit))
