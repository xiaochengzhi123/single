from __future__ import annotations

from dataclasses import dataclass

from signaltutor.agents.classifier import ProblemClassifier
from signaltutor.agents.direct_tutor import DirectTutor
from signaltutor.agents.model_adapter import QwenAgentsSDKModel
from signaltutor.agents.planner import SolutionPlanner
from signaltutor.agents.solver import Solver
from signaltutor.agents.tutor import TutorRenderer
from signaltutor.agents.verifier import Verifier
from signaltutor.agents.vision_parser import VisionProblemParser
from signaltutor.auth import AuthService
from signaltutor.config.settings import Settings, get_settings
from signaltutor.db.repositories.problems import InMemoryProblemRepository
from signaltutor.rag.repository import InMemoryKnowledgeRepository
from signaltutor.rag.retriever import KnowledgeRetriever
from signaltutor.schemas.problem import ProblemParse
from signaltutor.storage.local import LocalStorage
from signaltutor.students.repository import PersistentStudentRepository
from signaltutor.workflows.solve_problem import WorkflowContext


@dataclass
class Services:
    settings: Settings
    problems: InMemoryProblemRepository
    students: PersistentStudentRepository
    storage: LocalStorage
    vision: VisionProblemParser | None
    classifier: ProblemClassifier
    retriever: KnowledgeRetriever
    planner: SolutionPlanner
    solver: Solver
    verifier: Verifier
    tutor: TutorRenderer
    direct_tutor: DirectTutor
    auth: AuthService

    def workflow(self, problem_id: str, problem: ProblemParse) -> WorkflowContext:
        return WorkflowContext(
            problem_id=problem_id,
            problem=problem,
            settings=self.settings,
            classifier=self.classifier,
            retriever=self.retriever,
            planner=self.planner,
            solver=self.solver,
            verifier=self.verifier,
            tutor=self.tutor,
            students=self.students,
        )


def build_services(settings: Settings | None = None) -> Services:
    config = settings or get_settings()
    model = QwenAgentsSDKModel(config) if config.model_enabled else None
    return Services(
        settings=config,
        problems=InMemoryProblemRepository(),
        students=PersistentStudentRepository(config.learning_store_path),
        storage=LocalStorage(config.upload_dir, config.max_image_bytes),
        vision=VisionProblemParser(model, config) if model else None,
        classifier=ProblemClassifier(model, config),
        retriever=KnowledgeRetriever(InMemoryKnowledgeRepository.from_seed()),
        planner=SolutionPlanner(model, config),
        solver=Solver(model, config),
        verifier=Verifier(model, config),
        tutor=TutorRenderer(model, config),
        direct_tutor=DirectTutor(model, config),
        auth=AuthService(
            config.account_store_path,
            config.auth_secret,
            config.access_token_ttl_seconds,
        ),
    )


services = build_services()


def get_services() -> Services:
    return services
