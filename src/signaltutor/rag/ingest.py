from __future__ import annotations

from signaltutor.rag.repository import InMemoryKnowledgeRepository


def main() -> None:
    repository = InMemoryKnowledgeRepository.from_seed()
    print(
        f"Loaded {len(repository.concepts)} concepts, {len(repository.patterns)} patterns, "
        f"{len(repository.errors)} errors, {len(repository.examples)} examples."
    )


if __name__ == "__main__":
    main()
