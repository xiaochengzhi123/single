from pathlib import Path

from signaltutor.rag.knowledge_store import PersistentKnowledgeRepository
from signaltutor.schemas.knowledge import KnowledgeEntryCreate, KnowledgeEntryUpdate


async def test_knowledge_store_persists_and_filters_by_school(tmp_path: Path) -> None:
    repository = PersistentKnowledgeRepository(tmp_path / "knowledge.json", tmp_path / "no-seed")
    xidian = await repository.create(
        KnowledgeEntryCreate(
            title="西电 2025 年真题",
            content="求离散时间序列的 Z 变换并注明收敛域。",
            kind="past_exam",
            school="西安电子科技大学",
            year=2025,
            chapter="z_transform",
            topics=["Z 变换", "收敛域"],
            difficulty=4,
        )
    )
    await repository.create(
        KnowledgeEntryCreate(
            title="其他学校真题",
            content="求离散时间序列的 Z 变换并注明收敛域。",
            kind="past_exam",
            school="其他大学",
            chapter="z_transform",
            topics=["Z 变换"],
        )
    )

    reloaded = PersistentKnowledgeRepository(tmp_path / "knowledge.json", tmp_path / "no-seed")
    matches = await reloaded.search(
        "为什么 Z 变换必须写收敛域",
        school="西安电子科技大学",
        chapter="z_transform",
    )

    assert [entry.id for entry in matches] == [xidian.id]
    assert await reloaded.schools() == ["其他大学", "西安电子科技大学"]


async def test_unpublished_knowledge_is_not_retrieved(tmp_path: Path) -> None:
    repository = PersistentKnowledgeRepository(tmp_path / "knowledge.json", tmp_path / "no-seed")
    entry = await repository.create(
        KnowledgeEntryCreate(
            title="采样定理公式",
            content="采样频率必须大于最高频率的两倍。",
            kind="formula",
            chapter="sampling",
            topics=["采样定理"],
        )
    )
    await repository.update(entry.id, KnowledgeEntryUpdate(published=False))

    assert await repository.search("采样定理", chapter="sampling") == []
    assert len(await repository.list_entries(include_unpublished=True)) == 1
