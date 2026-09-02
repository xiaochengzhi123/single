import { authFetch } from "./auth";

export type AnswerMode = "full_solution" | "hint" | "guided" | "review_student_work";

export type UncertainElement = {
  description: string;
  location?: string | null;
  candidates: string[];
  confidence: number;
};

export type ProblemParse = {
  input_type: "text" | "image" | "text_image";
  question_text: string;
  known_conditions: string[];
  target: string;
  formulas: Array<{ raw?: string | null; latex: string; confidence: number }>;
  figures: Array<{ type: string; description: string }>;
  uncertain_elements: UncertainElement[];
  contains_student_work: boolean;
  student_steps: Array<{
    step_number: number;
    raw_expression?: string | null;
    normalized_latex?: string | null;
    description?: string | null;
  }>;
  signal_domain: "continuous_time" | "discrete_time" | "mixed" | "unknown";
  confidence: number;
};

export type SolveResponse = {
  status: "ok" | "needs_confirmation" | "needs_clarification" | "verification_failed";
  problem_id: string;
  problem_parse: ProblemParse;
  classification?: { chapter: string; topics: string[]; difficulty: number } | null;
  verification?: {
    is_correct: boolean;
    confidence: number;
    rule_checks_passed: string[];
    issues: Array<{ code: string; severity: string; message: string }>;
  } | null;
  answer?: string | null;
  clarification?: string | null;
  workflow_events: string[];
};

export type ChatAnswerResponse = {
  problem_id: string;
  answer_markdown: string;
  recognized_question?: string | null;
  response_kind: "solve" | "review_student_work" | "practice";
  chapter: string;
  topics: string[];
  exam_points: string[];
  common_mistakes: string[];
  score?: number | null;
  first_wrong_step?: number | null;
  error_code?: string | null;
  correction_summary?: string | null;
  confidence: number;
  needs_clarification: boolean;
  clarification?: string | null;
};

export type ChatMode = "solve" | "review_student_work";
export type AnswerStyle = "detailed" | "concise" | "hint";
export type ChatHistoryMessage = { role: "user" | "assistant"; content: string };
export type FeedbackRating = "helpful" | "not_helpful";

export type ChatOptions = {
  mode?: ChatMode;
  answerStyle?: AnswerStyle;
  history?: ChatHistoryMessage[];
  referenceQuestion?: string | null;
};

export type MistakeRecord = {
  id: string;
  problem_id?: string | null;
  question: string;
  answer_markdown: string;
  chapter: string;
  topics: string[];
  common_mistakes: string[];
  mastered: boolean;
  created_at: string;
};

export type LearningOverview = {
  student_id: string;
  topics: Array<{
    topic: string;
    mastery: number;
    attempts: number;
    correct_attempts: number;
    last_seen_at?: string | null;
  }>;
  mistakes: MistakeRecord[];
  open_mistakes: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function checked<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail?.message ?? body?.detail?.code ?? "请求失败，请稍后重试");
  }
  return response.json() as Promise<T>;
}

export async function answerText(
  content: string,
  options: ChatOptions = {},
  signal?: AbortSignal,
): Promise<ChatAnswerResponse> {
  return checked(
    await authFetch(`${API_BASE}/api/v1/chat/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        mode: options.mode ?? "solve",
        answer_style: options.answerStyle ?? "detailed",
        history: options.history ?? [],
        reference_question: options.referenceQuestion || null,
      }),
      signal,
    }),
  );
}

export async function answerImage(
  file: File,
  content: string,
  options: ChatOptions = {},
  signal?: AbortSignal,
): Promise<ChatAnswerResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("content", content);
  form.append("mode", options.mode ?? "solve");
  form.append("answer_style", options.answerStyle ?? "detailed");
  form.append("history_json", JSON.stringify(options.history ?? []));
  if (options.referenceQuestion) {
    form.append("reference_question", options.referenceQuestion);
  }
  return checked(
    await authFetch(`${API_BASE}/api/v1/chat/answer-image`, {
      method: "POST",
      body: form,
      signal,
    }),
  );
}

export async function generatePractice(
  source: ChatAnswerResponse,
  signal?: AbortSignal,
): Promise<ChatAnswerResponse> {
  return checked(
    await authFetch(`${API_BASE}/api/v1/practice/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_question: source.recognized_question || source.answer_markdown,
        chapter: source.chapter,
        topics: source.topics,
      }),
      signal,
    }),
  );
}

export async function generateTopicPractice(
  chapter: string,
  topic: string,
  signal?: AbortSignal,
): Promise<ChatAnswerResponse> {
  return checked(
    await authFetch(`${API_BASE}/api/v1/practice/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_question: `请针对 ${topic} 生成一道考研练习题`,
        chapter,
        topics: [topic],
      }),
      signal,
    }),
  );
}

export async function submitFeedback(
  problemId: string,
  rating: FeedbackRating,
): Promise<void> {
  await checked(
    await authFetch(`${API_BASE}/api/v1/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        problem_id: problemId,
        rating,
      }),
    }),
  );
}

export async function saveMistake(source: ChatAnswerResponse): Promise<MistakeRecord> {
  return checked(
    await authFetch(`${API_BASE}/api/v1/mistakes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        problem_id: source.problem_id,
        question: source.recognized_question || "图片题目",
        answer_markdown: source.answer_markdown,
        chapter: source.chapter,
        topics: source.topics,
        common_mistakes: source.common_mistakes,
      }),
    }),
  );
}

export async function fetchLearningOverview(): Promise<LearningOverview> {
  return checked(
    await authFetch(`${API_BASE}/api/v1/students/me/overview`, {
      cache: "no-store",
    }),
  );
}

export async function setMistakeMastered(
  mistakeId: string,
  mastered: boolean,
): Promise<MistakeRecord> {
  return checked(
    await authFetch(`${API_BASE}/api/v1/mistakes/${mistakeId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mastered }),
    }),
  );
}

export async function solveText(
  content: string,
  mode: AnswerMode,
  studentWork?: string,
  signal?: AbortSignal,
): Promise<SolveResponse> {
  return checked(
    await authFetch(`${API_BASE}/api/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        mode,
        student_work: studentWork || null,
      }),
      signal,
    }),
  );
}

export async function uploadProblem(file: File, signal?: AbortSignal): Promise<{
  status: "ok" | "needs_confirmation";
  problem_id: string;
  problem_parse: ProblemParse;
}> {
  const form = new FormData();
  form.append("file", file);
  return checked(
    await authFetch(`${API_BASE}/api/v1/problems/upload`, { method: "POST", body: form, signal }),
  );
}

export async function solveParsed(
  problemId: string,
  problem: ProblemParse,
  mode: AnswerMode,
  signal?: AbortSignal,
): Promise<SolveResponse> {
  return checked(
    await authFetch(`${API_BASE}/api/v1/problems/${problemId}/solve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode,
        confirmed_problem: problem,
      }),
      signal,
    }),
  );
}

export async function fetchMastery(): Promise<{
  topics: Array<{ topic: string; mastery: number; attempts: number }>;
}> {
  return checked(await authFetch(`${API_BASE}/api/v1/students/me/mastery`));
}
