from __future__ import annotations

from dataclasses import dataclass, field

from signaltutor.agents.classifier import ProblemClassifier
from signaltutor.agents.planner import SolutionPlanner
from signaltutor.agents.solver import Solver
from signaltutor.agents.tutor import TutorRenderer
from signaltutor.agents.verifier import Verifier
from signaltutor.config.settings import Settings
from signaltutor.rag.retriever import KnowledgeRetriever
from signaltutor.schemas.api import SolveProblemRequest, SolveProblemResponse
from signaltutor.schemas.problem import ProblemParse
from signaltutor.schemas.retrieval import RetrievalQuery
from signaltutor.schemas.solution import SolutionDraft, SolutionPlan
from signaltutor.students.repository import PersistentStudentRepository


@dataclass
class WorkflowContext:
    problem_id: str
    problem: ProblemParse
    settings: Settings
    classifier: ProblemClassifier
    retriever: KnowledgeRetriever
    planner: SolutionPlanner
    solver: Solver
    verifier: Verifier
    tutor: TutorRenderer
    students: PersistentStudentRepository
    events: list[str] = field(default_factory=list)


async def solve_problem(
    request: SolveProblemRequest,
    context: WorkflowContext,
) -> SolveProblemResponse:
    problem = request.confirmed_problem or context.problem
    events = context.events
    events.append("problem_parsed")
    if request.confirmed_problem is None and (
        problem.confidence < context.settings.vision_confidence_threshold
        or problem.uncertain_elements
    ):
        return SolveProblemResponse(
            status="needs_confirmation",
            problem_id=context.problem_id,
            problem_parse=problem,
            workflow_events=events,
        )

    classification = await context.classifier.classify(problem)
    events.append("classified")
    retrieval = await context.retriever.retrieve(
        RetrievalQuery(
            chapter=classification.chapter,
            topics=classification.topics,
            question=problem.question_text,
        )
    )
    events.append("retrieved")
    plan: SolutionPlan = await context.planner.plan(
        problem, classification, retrieval, request.mode
    )
    if plan.ambiguity_blockers:
        events.append("needs_clarification")
        clarification = "；".join(plan.ambiguity_blockers)
        return SolveProblemResponse(
            status="needs_clarification",
            problem_id=context.problem_id,
            problem_parse=problem,
            classification=classification,
            plan=plan,
            clarification=clarification,
            answer=f"题目信息不足：{clarification}。",
            workflow_events=events,
        )

    events.append("solving")
    solution: SolutionDraft = await context.solver.solve(
        problem, classification, retrieval, plan, request.mode
    )
    verification = await context.verifier.verify(problem, classification, retrieval, plan, solution)
    retry_count = 0
    while verification.retry_recommended and retry_count < context.settings.max_solver_retries:
        retry_count += 1
        feedback = "; ".join(issue.message for issue in verification.issues)
        solution = await context.solver.solve(
            problem, classification, retrieval, plan, request.mode, retry_feedback=feedback
        )
        verification = await context.verifier.verify(
            problem, classification, retrieval, plan, solution
        )
    if (
        verification.retry_recommended
        and context.settings.model_enabled
        and context.settings.enable_hard_model_fallback
    ):
        retry_count += 1
        feedback = "; ".join(issue.message for issue in verification.issues)
        solution = await context.solver.solve(
            problem,
            classification,
            retrieval,
            plan,
            request.mode,
            retry_feedback=feedback,
            model_override=context.settings.models.hard_fallback_model,
        )
        verification = await context.verifier.verify(
            problem, classification, retrieval, plan, solution
        )
    events.append("verified")
    answer = await context.tutor.render(
        problem, classification, retrieval, solution, verification, request.mode
    )
    if request.student_id:
        await context.students.record_attempt(
            request.student_id,
            [f"{classification.chapter}/{topic}" for topic in classification.topics],
            1.0 if verification.is_correct else 0.0,
            [issue.model_dump() for issue in verification.issues],
        )
    events.append("done")
    return SolveProblemResponse(
        status="ok" if verification.is_correct else "verification_failed",
        problem_id=context.problem_id,
        problem_parse=problem,
        classification=classification,
        plan=plan,
        solution=solution,
        verification=verification,
        answer=answer,
        workflow_events=events,
    )
