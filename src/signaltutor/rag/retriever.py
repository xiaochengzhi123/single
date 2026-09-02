from signaltutor.rag.repository import InMemoryKnowledgeRepository
from signaltutor.schemas.retrieval import RetrievalContext, RetrievalQuery


class KnowledgeRetriever:
    def __init__(self, repository: InMemoryKnowledgeRepository) -> None:
        self.repository = repository

    async def retrieve(self, query: RetrievalQuery) -> RetrievalContext:
        return await self.repository.retrieve(query)
