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
  source_type: "text" | "uploaded_image" | "ai_generated";
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
  sources: KnowledgeCitation[];
};

export type KnowledgeCitation = {
  entry_id: string;
  title: string;
  kind: "past_exam" | "textbook" | "formula" | "syllabus" | "solution" | "other";
  school?: string | null;
  year?: number | null;
  source_page?: number | null;
  source_url?: string | null;
  excerpt: string;
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
  targetSchool?: string | null;
};

export type MistakeRecord = {
  id: string;
  problem_id?: string | null;
  question: string;
  answer_markdown: string;
  source_type: "text" | "uploaded_image" | "ai_generated";
  has_image: boolean;
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

async function consumeAnswerStream(
  response: Response,
  onDelta: (text: string) => void,
): Promise<ChatAnswerResponse> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail?.message ?? body?.detail?.code ?? "请求失败，请稍后重试");
  }
  if (!response.body) throw new Error("当前浏览器不支持流式回答");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let completed: ChatAnswerResponse | null = null;

  const readLine = (line: string) => {
    if (!line.trim()) return;
    const event = JSON.parse(line) as {
      type: "delta" | "done";
      text?: string;
      response?: ChatAnswerResponse;
    };
    if (event.type === "delta" && event.text) onDelta(event.text);
    if (event.type === "done" && event.response) completed = event.response;
  };

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    lines.forEach(readLine);
    if (done) break;
  }
  if (buffer.trim()) readLine(buffer);
  if (!completed) throw new Error("回答流意外中断，请重新发送");
  return completed;
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
        target_school: options.targetSchool || null,
      }),
      signal,
    }),
  );
}

export async function streamAnswerText(
  content: string,
  options: ChatOptions,
  onDelta: (text: string) => void,
  signal?: AbortSignal,
): Promise<ChatAnswerResponse> {
  const response = await authFetch(`${API_BASE}/api/v1/chat/answer/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      content,
      mode: options.mode ?? "solve",
      answer_style: options.answerStyle ?? "detailed",
      history: options.history ?? [],
      reference_question: options.referenceQuestion || null,
      target_school: options.targetSchool || null,
    }),
    signal,
  });
  return consumeAnswerStream(response, onDelta);
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
  if (options.targetSchool) form.append("target_school", options.targetSchool);
  return checked(
    await authFetch(`${API_BASE}/api/v1/chat/answer-image`, {
      method: "POST",
      body: form,
      signal,
    }),
  );
}

export async function streamAnswerImage(
  file: File,
  content: string,
  options: ChatOptions,
  onDelta: (text: string) => void,
  signal?: AbortSignal,
): Promise<ChatAnswerResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("content", content);
  form.append("mode", options.mode ?? "solve");
  form.append("answer_style", options.answerStyle ?? "detailed");
  form.append("history_json", JSON.stringify(options.history ?? []));
  if (options.referenceQuestion) form.append("reference_question", options.referenceQuestion);
  if (options.targetSchool) form.append("target_school", options.targetSchool);
  const response = await authFetch(`${API_BASE}/api/v1/chat/answer-image/stream`, {
    method: "POST",
    body: form,
    signal,
  });
  return consumeAnswerStream(response, onDelta);
}

export async function generatePractice(
  source: ChatAnswerResponse,
  targetSchool?: string | null,
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
        target_school: targetSchool || null,
      }),
      signal,
    }),
  );
}

export async function streamGeneratePractice(
  source: ChatAnswerResponse,
  targetSchool: string | null,
  onDelta: (text: string) => void,
  signal?: AbortSignal,
): Promise<ChatAnswerResponse> {
  const response = await authFetch(`${API_BASE}/api/v1/practice/generate/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_question: source.recognized_question || source.answer_markdown,
      chapter: source.chapter,
      topics: source.topics,
      target_school: targetSchool || null,
    }),
    signal,
  });
  return consumeAnswerStream(response, onDelta);
}

export async function generateTopicPractice(
  chapter: string,
  topic: string,
  targetSchool?: string | null,
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
        target_school: targetSchool || null,
      }),
      signal,
    }),
  );
}

export async function streamGenerateTopicPractice(
  chapter: string,
  topic: string,
  targetSchool: string | null,
  onDelta: (text: string) => void,
  signal?: AbortSignal,
): Promise<ChatAnswerResponse> {
  const response = await authFetch(`${API_BASE}/api/v1/practice/generate/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_question: `请针对 ${topic} 生成一道考研练习题`,
      chapter,
      topics: [topic],
      target_school: targetSchool || null,
    }),
    signal,
  });
  return consumeAnswerStream(response, onDelta);
}

export async function fetchKnowledgeSchools(): Promise<string[]> {
  return checked(
    await authFetch(`${API_BASE}/api/v1/knowledge/schools`, { cache: "no-store" }),
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
  const generated = source.response_kind === "practice";
  return checked(
    await authFetch(`${API_BASE}/api/v1/mistakes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        problem_id: source.problem_id,
        question: generated
          ? source.answer_markdown
          : source.recognized_question || "图片题目",
        answer_markdown: generated ? "" : source.answer_markdown,
        source_type: generated ? "ai_generated" : source.source_type,
        chapter: source.chapter,
        topics: source.topics,
        common_mistakes: source.common_mistakes,
      }),
    }),
  );
}

export async function fetchMistakeImage(mistakeId: string): Promise<Blob> {
  const response = await authFetch(`${API_BASE}/api/v1/mistakes/${mistakeId}/image`, {
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail?.message ?? "题目图片加载失败");
  }
  return response.blob();
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
