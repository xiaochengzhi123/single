"use client";

import {
  ArrowBendUpLeft,
  ArrowClockwise,
  ArrowUp,
  BookBookmark,
  CaretLeft,
  CheckCircle,
  ChartBar,
  ClipboardText,
  Copy,
  Function,
  List,
  Paperclip,
  Plus,
  ShieldCheck,
  SidebarSimple,
  SignOut,
  Sparkle,
  Stop,
  ThumbsDown,
  ThumbsUp,
  Trash,
  WarningCircle,
  X,
} from "@phosphor-icons/react";
import {
  ChangeEvent,
  ClipboardEvent,
  DragEvent,
  FormEvent,
  KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  AnswerStyle,
  ChatAnswerResponse,
  FeedbackRating,
  fetchKnowledgeSchools,
  fetchLearningOverview,
  fetchMistakeImage,
  LearningOverview,
  MistakeRecord,
  saveMistake,
  setMistakeMastered,
  solveText,
  streamAnswerImage,
  streamAnswerText,
  streamGeneratePractice,
  streamGenerateTopicPractice,
  submitFeedback,
} from "../lib/api";
import { AuthUser } from "../lib/auth";
import { MarkdownMath } from "./MarkdownMath";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  imageUrl?: string;
  hadImage?: boolean;
  analysis?: ChatAnswerResponse;
  answerStyle?: AnswerStyle;
  strict?: boolean;
  feedback?: FeedbackRating;
};

type StoredConversation = {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
};

type Attachment = {
  file: File;
  url: string;
};

const suggestions = [
  "讲清楚卷积积分的上下限怎么判断",
  "求一个信号的傅里叶变换",
  "为什么 Z 变换必须写收敛域",
  "检查我的拉普拉斯变换步骤",
];

const answerStyles: Array<{ value: AnswerStyle; label: string; title: string }> = [
  { value: "detailed", label: "详细", title: "完整推导与考研规范答案" },
  { value: "concise", label: "简洁", title: "只保留结论与关键步骤" },
  { value: "hint", label: "提示", title: "只给思路与下一步，不直接揭晓答案" },
];

const chapterNames: Record<string, string> = {
  signals: "信号基础",
  lti: "LTI 系统",
  fourier_series: "傅里叶级数",
  fourier_transform: "傅里叶变换",
  laplace: "拉普拉斯变换",
  z_transform: "Z 变换",
  sampling: "采样",
  system_properties: "系统性质",
};

const knowledgeKindNames: Record<string, string> = {
  past_exam: "历年真题",
  textbook: "教材",
  formula: "公式",
  syllabus: "考试范围",
  solution: "标准解法",
  other: "参考资料",
};

function newId() {
  return globalThis.crypto?.randomUUID?.() ??
    `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function answerFrom(response: ChatAnswerResponse) {
  if (response.answer_markdown) return response.answer_markdown;
  if (response.clarification) return `还需要你补充一点信息：\n\n${response.clarification}`;
  return "这道题目前还不能可靠作答。请补充题目条件，或换一张更清晰的图片。";
}

function conversationTitle(messages: ChatMessage[]) {
  const firstQuestion = messages.find((message) => message.role === "user")?.content.trim();
  return firstQuestion ? firstQuestion.slice(0, 24) : "新的对话";
}

function historyForModel(messages: ChatMessage[]) {
  return messages
    .filter((message) => message.content.trim())
    .slice(-12)
    .map((message) => ({
      role: message.role,
      content: message.content.slice(0, 4000),
    }));
}

function messagesForStorage(messages: ChatMessage[]) {
  return messages.slice(-80).map((message) => ({
    ...message,
    imageUrl: undefined,
    hadImage: Boolean(message.imageUrl || message.hadImage),
    analysis: message.analysis
      ? { ...message.analysis, answer_markdown: "" }
      : undefined,
  }));
}

function messagesFromStorage(messages: ChatMessage[]) {
  return messages.map((message) => ({
    ...message,
    imageUrl: undefined,
    analysis: message.analysis
      ? {
          ...message.analysis,
          answer_markdown: message.analysis.answer_markdown || message.content,
        }
      : undefined,
  }));
}

export function TutorWorkbench({ user, onLogout }: { user: AuthUser; onLogout: () => void }) {
  const conversationStorageKey = `signaltutor.conversations.v2.${user.id}`;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState(newId);
  const [conversations, setConversations] = useState<StoredConversation[]>([]);
  const [historyReady, setHistoryReady] = useState(false);
  const [input, setInput] = useState("");
  const [attachment, setAttachment] = useState<Attachment | null>(null);
  const [busy, setBusy] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [composerMode, setComposerMode] = useState<"solve" | "review_student_work">("solve");
  const [answerStyle, setAnswerStyle] = useState<AnswerStyle>("detailed");
  const [knowledgeSchools, setKnowledgeSchools] = useState<string[]>([]);
  const [targetSchool, setTargetSchool] = useState("");
  const [referenceQuestion, setReferenceQuestion] = useState<string | null>(null);
  const [learningOverview, setLearningOverview] = useState<LearningOverview | null>(null);
  const [learningPanelOpen, setLearningPanelOpen] = useState(false);
  const [selectedMistake, setSelectedMistake] = useState<MistakeRecord | null>(null);
  const [mistakeImageUrl, setMistakeImageUrl] = useState<string | null>(null);
  const [mistakeImageLoading, setMistakeImageLoading] = useState(false);
  const [savedProblemIds, setSavedProblemIds] = useState<string[]>([]);
  const [savingProblemId, setSavingProblemId] = useState<string | null>(null);
  const [feedbackProblemId, setFeedbackProblemId] = useState<string | null>(null);
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const objectUrlsRef = useRef<string[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const streamingMessageIdRef = useRef<string | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, busy]);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(conversationStorageKey) || "[]");
      if (Array.isArray(saved) && saved.length > 0) {
        const restored = (saved as StoredConversation[])
          .filter((item) => item?.id && Array.isArray(item.messages))
          .sort((left, right) => right.updatedAt - left.updatedAt)
          .slice(0, 30);
        if (restored.length > 0) {
          setConversations(restored);
          setConversationId(restored[0].id);
          setMessages(messagesFromStorage(restored[0].messages));
        }
      }
    } catch {
      localStorage.removeItem(conversationStorageKey);
    } finally {
      setHistoryReady(true);
    }
  }, [conversationStorageKey]);

  useEffect(() => {
    if (!historyReady || messages.length === 0) return;
    const now = Date.now();
    setConversations((current) => {
      const existing = current.find((item) => item.id === conversationId);
      const next: StoredConversation = {
        id: conversationId,
        title: conversationTitle(messages),
        messages: messagesForStorage(messages),
        createdAt: existing?.createdAt ?? now,
        updatedAt: now,
      };
      return [next, ...current.filter((item) => item.id !== conversationId)]
        .sort((left, right) => right.updatedAt - left.updatedAt)
        .slice(0, 30);
    });
  }, [conversationId, historyReady, messages]);

  useEffect(() => {
    if (!historyReady) return;
    try {
      localStorage.setItem(conversationStorageKey, JSON.stringify(conversations));
    } catch {
      setError("本地对话记录空间已满，请删除部分历史对话");
    }
  }, [conversationStorageKey, conversations, historyReady]);

  useEffect(() => {
    if (!previewImageUrl) return;
    const closeOnEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") setPreviewImageUrl(null);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [previewImageUrl]);

  useEffect(() => {
    if (!mistakeImageUrl) return;
    return () => URL.revokeObjectURL(mistakeImageUrl);
  }, [mistakeImageUrl]);

  useEffect(() => {
    const urls = objectUrlsRef.current;
    return () => urls.forEach((url) => URL.revokeObjectURL(url));
  }, []);

  useEffect(() => {
    void refreshLearningOverview();
    void fetchKnowledgeSchools().then(setKnowledgeSchools).catch(() => setKnowledgeSchools([]));
  }, []);

  async function refreshLearningOverview() {
    try {
      const overview = await fetchLearningOverview();
      setLearningOverview(overview);
      setSavedProblemIds(
        overview.mistakes
          .map((mistake) => mistake.problem_id)
          .filter((problemId): problemId is string => Boolean(problemId)),
      );
    } catch {
      setLearningOverview(null);
    }
  }

  function chooseFile(file: File) {
    if (!file.type.startsWith("image/")) {
      setError("请选择 JPG、PNG 或 WEBP 图片");
      return;
    }
    if (attachment) {
      URL.revokeObjectURL(attachment.url);
      objectUrlsRef.current = objectUrlsRef.current.filter(
        (url) => url !== attachment.url,
      );
    }
    const url = URL.createObjectURL(file);
    objectUrlsRef.current.push(url);
    setAttachment({ file, url });
    setError(null);
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) chooseFile(file);
    event.target.value = "";
  }

  function onDrop(event: DragEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file) chooseFile(file);
  }

  function onComposerPaste(event: ClipboardEvent<HTMLFormElement>) {
    const imageItem = Array.from(event.clipboardData.items).find(
      (item) => item.kind === "file" && item.type.startsWith("image/"),
    );
    const image = imageItem?.getAsFile();
    if (!image) return;
    event.preventDefault();
    chooseFile(image);
  }

  function removeAttachment() {
    if (attachment) {
      URL.revokeObjectURL(attachment.url);
      objectUrlsRef.current = objectUrlsRef.current.filter((url) => url !== attachment.url);
    }
    setAttachment(null);
  }

  async function sendMessage() {
    const prompt = input.trim();
    const selectedImage = attachment;
    if ((!prompt && !selectedImage) || busy) return;

    const userText = prompt || "请解答图片中的题目";
    const streamingMessageId = newId();
    streamingMessageIdRef.current = streamingMessageId;
    setMessages((current) => [
      ...current,
      {
        id: newId(),
        role: "user",
        content: userText,
        imageUrl: selectedImage?.url,
        hadImage: Boolean(selectedImage),
      },
      {
        id: streamingMessageId,
        role: "assistant",
        content: "",
        answerStyle,
      },
    ]);
    setInput("");
    setAttachment(null);
    setError(null);
    setBusy(true);
    const mode = composerMode;
    const referencedQuestion = referenceQuestion;
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const onDelta = (text: string) => {
        setStatusText("");
        setMessages((current) => current.map((message) => (
          message.id === streamingMessageId
            ? { ...message, content: message.content + text }
            : message
        )));
      };
      const finish = (response: ChatAnswerResponse) => {
        setMessages((current) => current.map((message) => (
          message.id === streamingMessageId
            ? {
                ...message,
                content: answerFrom(response),
                analysis: response,
                answerStyle,
              }
            : message
        )));
      };
      if (!selectedImage) {
        setStatusText("正在思考");
        finish(
          await streamAnswerText(
            prompt,
            {
              mode,
              answerStyle,
              history: historyForModel(messages),
              referenceQuestion: referencedQuestion,
              targetSchool,
            },
            onDelta,
            controller.signal,
          ),
        );
        if (mode === "review_student_work") {
          await refreshLearningOverview();
        }
        return;
      }

      setStatusText("正在识别并解答");
      finish(
        await streamAnswerImage(
          selectedImage.file,
          prompt,
          {
            mode,
            answerStyle,
            history: historyForModel(messages),
            referenceQuestion: referencedQuestion,
            targetSchool,
          },
          onDelta,
          controller.signal,
        ),
      );
      if (mode === "review_student_work") {
        await refreshLearningOverview();
      }
    } catch (caught) {
      if (!controller.signal.aborted) {
        setMessages((current) => current.map((message) => (
          message.id === streamingMessageId && !message.content
            ? { ...message, content: "回答生成中断，请重新发送。" }
            : message
        )));
        setError(caught instanceof Error ? caught.message : "请求失败，请稍后重试");
      }
    } finally {
      if (streamingMessageIdRef.current === streamingMessageId) {
        streamingMessageIdRef.current = null;
      }
      if (abortRef.current === controller) abortRef.current = null;
      setBusy(false);
      setStatusText("");
      if (!controller.signal.aborted) {
        setComposerMode("solve");
        setReferenceQuestion(null);
      }
    }
  }

  function beginReview(source: ChatAnswerResponse) {
    const question = source.response_kind === "practice"
      ? source.answer_markdown
      : source.recognized_question || source.answer_markdown;
    setComposerMode("review_student_work");
    setReferenceQuestion(question);
    setInput("");
    setError(null);
    window.setTimeout(() => textareaRef.current?.focus(), 0);
  }

  function cancelReview() {
    setComposerMode("solve");
    setReferenceQuestion(null);
  }

  async function createSimilar(source: ChatAnswerResponse) {
    if (busy) return;
    const streamingMessageId = newId();
    streamingMessageIdRef.current = streamingMessageId;
    setMessages((current) => [
      ...current,
      { id: newId(), role: "user", content: "给我一道同类题" },
      { id: streamingMessageId, role: "assistant", content: "", answerStyle },
    ]);
    setBusy(true);
    setError(null);
    setStatusText("正在生成同类题");
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await streamGeneratePractice(
        source,
        targetSchool || null,
        (text) => {
          setStatusText("");
          setMessages((current) => current.map((message) => (
            message.id === streamingMessageId
              ? { ...message, content: message.content + text }
              : message
          )));
        },
        controller.signal,
      );
      setMessages((current) => current.map((message) => (
        message.id === streamingMessageId
          ? { ...message, content: answerFrom(response), analysis: response, answerStyle }
          : message
      )));
    } catch (caught) {
      if (!controller.signal.aborted) {
        setMessages((current) => current.map((message) => (
          message.id === streamingMessageId && !message.content
            ? { ...message, content: "同类题生成中断，请重新尝试。" }
            : message
        )));
        setError(caught instanceof Error ? caught.message : "同类题生成失败");
      }
    } finally {
      if (streamingMessageIdRef.current === streamingMessageId) {
        streamingMessageIdRef.current = null;
      }
      if (abortRef.current === controller) abortRef.current = null;
      setBusy(false);
      setStatusText("");
    }
  }

  async function addToMistakes(source: ChatAnswerResponse) {
    if (savingProblemId) return;
    setSavingProblemId(source.problem_id);
    setError(null);
    try {
      await saveMistake(source);
      setSavedProblemIds((current) => [...new Set([...current, source.problem_id])]);
      await refreshLearningOverview();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "保存错题失败");
    } finally {
      setSavingProblemId(null);
    }
  }

  async function openMistake(mistake: MistakeRecord) {
    setSelectedMistake(mistake);
    setMistakeImageUrl(null);
    setMistakeImageLoading(mistake.has_image);
    if (!mistake.has_image) return;
    try {
      const image = await fetchMistakeImage(mistake.id);
      setMistakeImageUrl(URL.createObjectURL(image));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "题目图片加载失败");
    } finally {
      setMistakeImageLoading(false);
    }
  }

  async function rateAnswer(
    messageId: string,
    source: ChatAnswerResponse,
    rating: FeedbackRating,
  ) {
    if (feedbackProblemId) return;
    setFeedbackProblemId(source.problem_id);
    setError(null);
    try {
      await submitFeedback(source.problem_id, rating);
      setMessages((current) => current.map((message) => (
        message.id === messageId ? { ...message, feedback: rating } : message
      )));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "评价提交失败");
    } finally {
      setFeedbackProblemId(null);
    }
  }

  async function practiceWeakTopic(topicKey: string) {
    if (busy) return;
    const [chapter, ...topicParts] = topicKey.split("/");
    const topic = topicParts.join("/") || topicKey;
    const streamingMessageId = newId();
    streamingMessageIdRef.current = streamingMessageId;
    setLearningPanelOpen(false);
    setMessages((current) => [
      ...current,
      { id: newId(), role: "user", content: `针对薄弱考点“${topic}”给我一道练习题` },
      { id: streamingMessageId, role: "assistant", content: "", answerStyle },
    ]);
    setBusy(true);
    setError(null);
    setStatusText("正在生成针对性练习");
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await streamGenerateTopicPractice(
        chapter,
        topic,
        targetSchool || null,
        (text) => {
          setStatusText("");
          setMessages((current) => current.map((message) => (
            message.id === streamingMessageId
              ? { ...message, content: message.content + text }
              : message
          )));
        },
        controller.signal,
      );
      setMessages((current) => current.map((message) => (
        message.id === streamingMessageId
          ? { ...message, content: answerFrom(response), analysis: response, answerStyle }
          : message
      )));
    } catch (caught) {
      if (!controller.signal.aborted) {
        setMessages((current) => current.map((message) => (
          message.id === streamingMessageId && !message.content
            ? { ...message, content: "练习题生成中断，请重新尝试。" }
            : message
        )));
        setError(caught instanceof Error ? caught.message : "练习题生成失败");
      }
    } finally {
      if (streamingMessageIdRef.current === streamingMessageId) {
        streamingMessageIdRef.current = null;
      }
      if (abortRef.current === controller) abortRef.current = null;
      setBusy(false);
      setStatusText("");
    }
  }

  function askMistakeAgain(question: string) {
    setLearningPanelOpen(false);
    setSelectedMistake(null);
    setMistakeImageUrl(null);
    setInput(question);
    setError(null);
    window.setTimeout(() => textareaRef.current?.focus(), 0);
  }

  async function runStrictVerification(source: ChatAnswerResponse) {
    if (busy) return;
    const question = source.recognized_question || source.answer_markdown;
    setMessages((current) => [
      ...current,
      { id: newId(), role: "user", content: "请进行严格校验" },
    ]);
    setBusy(true);
    setError(null);
    setStatusText("正在执行严格校验");
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const result = await solveText(question, "full_solution", undefined, controller.signal);
      setMessages((current) => [
        ...current,
        {
          id: newId(),
          role: "assistant",
          content: result.answer || result.clarification || "严格校验未能形成结论。",
          strict: true,
        },
      ]);
      await refreshLearningOverview();
    } catch (caught) {
      if (!controller.signal.aborted) {
        setError(caught instanceof Error ? caught.message : "严格校验失败");
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null;
      setBusy(false);
      setStatusText("");
    }
  }

  async function regenerateAnswer(messageId: string, source: ChatAnswerResponse) {
    if (busy) return;
    const question = source.recognized_question || source.answer_markdown;
    setBusy(true);
    setError(null);
    setStatusText(answerStyle === "hint" ? "正在生成提示" : "正在重新回答");
    const controller = new AbortController();
    abortRef.current = controller;
    streamingMessageIdRef.current = messageId;
    try {
      const messageIndex = messages.findIndex((message) => message.id === messageId);
      const priorMessages = messageIndex >= 0 ? messages.slice(0, messageIndex) : messages;
      setMessages((current) => current.map((message) => (
        message.id === messageId ? { ...message, content: "", analysis: undefined } : message
      )));
      const response = await streamAnswerText(
        question,
        {
          mode: "solve",
          answerStyle,
          history: historyForModel(priorMessages),
          targetSchool,
        },
        (text) => {
          setStatusText("");
          setMessages((current) => current.map((message) => (
            message.id === messageId
              ? { ...message, content: message.content + text }
              : message
          )));
        },
        controller.signal,
      );
      setMessages((current) => current.map((message) => (
        message.id === messageId
          ? {
              ...message,
              content: answerFrom(response),
              analysis: response,
              answerStyle,
            }
          : message
      )));
    } catch (caught) {
      if (!controller.signal.aborted) {
        setError(caught instanceof Error ? caught.message : "重新回答失败");
      }
    } finally {
      if (streamingMessageIdRef.current === messageId) {
        streamingMessageIdRef.current = null;
      }
      if (abortRef.current === controller) abortRef.current = null;
      setBusy(false);
      setStatusText("");
    }
  }

  async function toggleMistakeMastery(mistakeId: string, mastered: boolean) {
    try {
      const updated = await setMistakeMastered(mistakeId, mastered);
      setSelectedMistake((current) => (
        current?.id === mistakeId ? { ...current, mastered: updated.mastered } : current
      ));
      await refreshLearningOverview();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "更新错题状态失败");
    }
  }

  function stopResponse() {
    abortRef.current?.abort();
    abortRef.current = null;
    setBusy(false);
    setStatusText("");
    const streamingMessageId = streamingMessageIdRef.current;
    streamingMessageIdRef.current = null;
    setMessages((current) => {
      if (!streamingMessageId) {
        return [...current, { id: newId(), role: "assistant", content: "已停止生成。" }];
      }
      return current.map((message) => (
        message.id === streamingMessageId
          ? {
              ...message,
              content: message.content
                ? `${message.content}\n\n> 已停止生成。`
                : "已停止生成。",
            }
          : message
      ));
    });
  }

  function releaseObjectUrls() {
    objectUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    objectUrlsRef.current = [];
  }

  function startNewChat() {
    abortRef.current?.abort();
    abortRef.current = null;
    releaseObjectUrls();
    setConversationId(newId());
    setMessages([]);
    setInput("");
    setAttachment(null);
    setComposerMode("solve");
    setReferenceQuestion(null);
    setError(null);
    setSidebarOpen(false);
  }

  function openConversation(conversation: StoredConversation) {
    abortRef.current?.abort();
    abortRef.current = null;
    releaseObjectUrls();
    setConversationId(conversation.id);
    setMessages(messagesFromStorage(conversation.messages));
    setInput("");
    setAttachment(null);
    setComposerMode("solve");
    setReferenceQuestion(null);
    setError(null);
    setBusy(false);
    setStatusText("");
    setSidebarOpen(false);
  }

  function deleteConversation(id: string) {
    setConversations((current) => current.filter((item) => item.id !== id));
    if (id === conversationId) startNewChat();
  }

  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void sendMessage();
    }
  }

  function onComposerSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!busy) void sendMessage();
  }

  return (
    <main className="chat-app">
      <div
        className={sidebarOpen ? "sidebar-backdrop visible" : "sidebar-backdrop"}
        onClick={() => setSidebarOpen(false)}
        aria-hidden="true"
      />

      <aside className={sidebarOpen ? "chat-sidebar open" : "chat-sidebar"}>
        <div className="sidebar-top">
          <a className="chat-brand" href="#chat" aria-label="SignalTutor 首页">
            <span className="brand-symbol"><Function size={19} weight="bold" /></span>
            <span>SignalTutor</span>
          </a>
          <button
            className="icon-control sidebar-close"
            type="button"
            aria-label="关闭侧栏"
            onClick={() => setSidebarOpen(false)}
          >
            <SidebarSimple size={20} />
          </button>
        </div>

        <button className="new-chat-button" type="button" onClick={startNewChat}>
          <Plus size={18} />
          <span>新对话</span>
        </button>

        <div className="history-section">
          <p className="history-label">最近</p>
          <div className="history-list">
            {conversations.length ? conversations.map((conversation) => (
              <div
                className={conversation.id === conversationId ? "history-row active" : "history-row"}
                key={conversation.id}
              >
                <button
                  className="history-item"
                  type="button"
                  onClick={() => openConversation(conversation)}
                  aria-current={conversation.id === conversationId ? "page" : undefined}
                >
                  <span>{conversation.title}</span>
                </button>
                <button
                  className="history-delete"
                  type="button"
                  aria-label={`删除对话：${conversation.title}`}
                  title="删除对话"
                  onClick={() => deleteConversation(conversation.id)}
                >
                  <Trash size={14} />
                </button>
              </div>
            )) : (
              <p className="history-empty">发送第一条消息后，会自动保存在这里。</p>
            )}
          </div>
        </div>

        <div className="learning-summary">
          <p className="history-label">学习记录</p>
          <button
            className="learning-entry"
            type="button"
            onClick={() => {
              setLearningPanelOpen(true);
              setSidebarOpen(false);
            }}
          >
            <BookBookmark size={17} />
            <span>错题本</span>
            <strong>{learningOverview?.open_mistakes ?? 0}</strong>
          </button>
          <button
            className="learning-entry"
            type="button"
            onClick={() => {
              setLearningPanelOpen(true);
              setSidebarOpen(false);
            }}
          >
            <ChartBar size={17} />
            <span>薄弱考点</span>
            <strong>{learningOverview?.topics.length ?? 0}</strong>
          </button>
        </div>

        <div className="sidebar-footer">
          <span className="footer-icon"><Function size={17} /></span>
          <div>
            <strong>{user.display_name}</strong>
            <span>{user.username}</span>
          </div>
          <button type="button" aria-label="退出登录" title="退出登录" onClick={onLogout}>
            <SignOut size={17} />
          </button>
        </div>
      </aside>

      <section className="chat-stage" id="chat" aria-label="信号与系统对话">
        <header className="chat-header">
          <button
            className="icon-control mobile-menu"
            type="button"
            aria-label="打开侧栏"
            onClick={() => setSidebarOpen(true)}
          >
            <List size={21} />
          </button>
          <div className="header-title">
            <strong>信号与系统考研助手</strong>
          </div>
          <button
            className="icon-control mobile-new-chat"
            type="button"
            aria-label="新对话"
            onClick={startNewChat}
          >
            <Plus size={20} />
          </button>
        </header>

        <div className={messages.length ? "chat-scroll" : "chat-scroll empty"}>
          {messages.length === 0 ? (
            <section className="welcome-state" aria-labelledby="welcome-title">
              <span className="welcome-mark"><Function size={26} weight="bold" /></span>
              <h1 id="welcome-title">今天想攻克哪道题？</h1>
              <p>发来题目、公式或截图，我会按考研答题规范一步步讲清楚。</p>
              <div className="suggestion-grid">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => setInput(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </section>
          ) : (
            <div className="message-list">
              {messages.map((message) => (
                <article
                  className={`message-row ${message.role}`}
                  key={message.id}
                >
                  {message.role === "assistant" && (
                    <span className="assistant-avatar" aria-hidden="true">
                      <Function size={17} weight="bold" />
                    </span>
                  )}
                  <div className="message-body">
                    {message.imageUrl && (
                      <button
                        className="message-image-button"
                        type="button"
                        onClick={() => setPreviewImageUrl(message.imageUrl!)}
                        aria-label="放大查看题目图片"
                      >
                        <img
                          className="message-image"
                          src={message.imageUrl}
                          alt="用户上传的题目图片"
                        />
                        <span>点击放大</span>
                      </button>
                    )}
                    {!message.imageUrl && message.hadImage && (
                      <span className="stored-image-note">本题包含图片，重新打开后保留文字与回答</span>
                    )}
                    {message.role === "assistant" ? (
                      <div
                        className={
                          busy && streamingMessageIdRef.current === message.id
                            ? "streaming-answer"
                            : undefined
                        }
                      >
                        <MarkdownMath content={message.content} />
                      </div>
                    ) : (
                      <p>{message.content}</p>
                    )}
                    {message.analysis && message.analysis.confidence > 0 && (
                      <div className="answer-insights">
                        <div className="answer-context">
                          <span>{chapterNames[message.analysis.chapter] ?? message.analysis.chapter}</span>
                          {message.analysis.topics.slice(0, 3).map((topic) => (
                            <span key={topic}>{topic}</span>
                          ))}
                          {message.analysis.score !== null && message.analysis.score !== undefined && (
                            <strong>{Math.round(message.analysis.score)} 分</strong>
                          )}
                        </div>
                        {(message.analysis.exam_points.length > 0 || message.analysis.common_mistakes.length > 0) && (
                          <div className="insight-grid">
                            {message.analysis.exam_points.length > 0 && (
                              <section>
                                <h3><ClipboardText size={16} />阅卷得分点</h3>
                                <ul>
                                  {message.analysis.exam_points.map((point) => (
                                    <li key={point}><MarkdownMath content={point} /></li>
                                  ))}
                                </ul>
                              </section>
                            )}
                            {message.analysis.common_mistakes.length > 0 && (
                              <section>
                                <h3><WarningCircle size={16} />关键易错点</h3>
                                <ul>
                                  {message.analysis.common_mistakes.map((mistake) => (
                                    <li key={mistake}><MarkdownMath content={mistake} /></li>
                                  ))}
                                </ul>
                              </section>
                            )}
                          </div>
                        )}
                        {message.analysis.response_kind === "review_student_work" && message.analysis.correction_summary && (
                          <div className="correction-summary">
                            <strong>
                              {message.analysis.first_wrong_step
                                ? `第一处错误在第 ${message.analysis.first_wrong_step} 步：`
                                : "修正建议："}
                            </strong>
                            <MarkdownMath content={message.analysis.correction_summary} />
                          </div>
                        )}
                      </div>
                    )}
                    {message.analysis?.sources?.length ? (
                      <section className="answer-sources" aria-label="参考来源">
                        <h3><BookBookmark size={16} />参考来源</h3>
                        <div className="source-list">
                          {message.analysis.sources.map((source, index) => (
                            <a
                              className="source-card"
                              key={source.entry_id}
                              href={source.source_url || undefined}
                              target={source.source_url ? "_blank" : undefined}
                              rel={source.source_url ? "noreferrer" : undefined}
                              onClick={source.source_url ? undefined : (event) => event.preventDefault()}
                            >
                              <span>资料 {index + 1}</span>
                              <strong>{source.title}</strong>
                              <small>
                                {[source.school, source.year ? `${source.year} 年` : null, source.source_page ? `第 ${source.source_page} 页` : null, knowledgeKindNames[source.kind]].filter(Boolean).join(" · ")}
                              </small>
                              <p>{source.excerpt}</p>
                            </a>
                          ))}
                        </div>
                      </section>
                    ) : null}
                    {message.strict && (
                      <div className="strict-result-label">
                        <ShieldCheck size={16} weight="fill" />
                        严格校验结果
                      </div>
                    )}
                    {message.role === "assistant" && (
                      <div className="answer-details">
                        {message.analysis && message.analysis.confidence > 0 && message.analysis.response_kind !== "review_student_work" && (
                          <button
                            type="button"
                            onClick={() => beginReview(message.analysis!)}
                            disabled={busy}
                          >
                            <ClipboardText size={16} />
                            检查我的解法
                          </button>
                        )}
                        {message.analysis && message.analysis.confidence > 0 && message.analysis.response_kind === "solve" && (
                          <button
                            type="button"
                            onClick={() => void createSimilar(message.analysis!)}
                            disabled={busy}
                          >
                            <Sparkle size={16} />
                            同类题
                          </button>
                        )}
                        {message.analysis && message.analysis.confidence > 0 && (
                          <button
                            type="button"
                            onClick={() => void addToMistakes(message.analysis!)}
                            disabled={savingProblemId === message.analysis.problem_id}
                          >
                            <BookBookmark
                              size={16}
                              weight={savedProblemIds.includes(message.analysis.problem_id) ? "fill" : "regular"}
                            />
                            {savedProblemIds.includes(message.analysis.problem_id) ? "已加入" : "加入错题"}
                          </button>
                        )}
                        {message.analysis && message.analysis.confidence > 0 && message.analysis.response_kind === "solve" && (
                          <button
                            type="button"
                            onClick={() => void runStrictVerification(message.analysis!)}
                            disabled={busy}
                          >
                            <ShieldCheck size={16} />
                            严格校验
                          </button>
                        )}
                        <span className="answer-utilities">
                          {message.analysis && message.analysis.confidence > 0 && message.analysis.response_kind === "solve" && (
                            <button
                              type="button"
                              aria-label={`按${answerStyles.find((item) => item.value === answerStyle)?.label}模式重新回答`}
                              title={`按当前${answerStyles.find((item) => item.value === answerStyle)?.label}模式重新回答`}
                              className="regenerate-answer"
                              onClick={() => void regenerateAnswer(message.id, message.analysis!)}
                              disabled={busy}
                            >
                              <ArrowClockwise size={16} />
                            </button>
                          )}
                          {message.analysis && message.analysis.confidence > 0 && (
                            <>
                              <button
                                type="button"
                                aria-label="回答有帮助"
                                title="回答有帮助"
                                aria-pressed={message.feedback === "helpful"}
                                className={message.feedback === "helpful" ? "feedback-answer active" : "feedback-answer"}
                                onClick={() => void rateAnswer(message.id, message.analysis!, "helpful")}
                                disabled={feedbackProblemId === message.analysis.problem_id}
                              >
                                <ThumbsUp size={16} weight={message.feedback === "helpful" ? "fill" : "regular"} />
                              </button>
                              <button
                                type="button"
                                aria-label="回答没有帮助"
                                title="回答没有帮助"
                                aria-pressed={message.feedback === "not_helpful"}
                                className={message.feedback === "not_helpful" ? "feedback-answer active" : "feedback-answer"}
                                onClick={() => void rateAnswer(message.id, message.analysis!, "not_helpful")}
                                disabled={feedbackProblemId === message.analysis.problem_id}
                              >
                                <ThumbsDown size={16} weight={message.feedback === "not_helpful" ? "fill" : "regular"} />
                              </button>
                            </>
                          )}
                          <button
                            type="button"
                            aria-label="复制回答"
                            title="复制回答"
                            className="copy-answer"
                            onClick={() => void navigator.clipboard.writeText(message.content)}
                          >
                            <Copy size={16} />
                          </button>
                        </span>
                      </div>
                    )}
                  </div>
                </article>
              ))}

              {busy && (
                <div className="thinking-row" aria-live="polite">
                  <span className="assistant-avatar" aria-hidden="true">
                    <Function size={17} weight="bold" />
                  </span>
                  <div>
                    <span className="thinking-label">{statusText}</span>
                    <span className="thinking-dots" aria-hidden="true">
                      <i />
                      <i />
                      <i />
                    </span>
                  </div>
                </div>
              )}

              {error && (
                <div className="chat-error" role="alert">
                  <WarningCircle size={19} />
                  <div>
                    <strong>暂时无法回答</strong>
                    <p>{error}</p>
                  </div>
                </div>
              )}
              <div ref={endRef} />
            </div>
          )}
        </div>

        <div className="composer-zone">
          <form
            className="chat-composer"
            onSubmit={onComposerSubmit}
            onPaste={onComposerPaste}
            onDrop={onDrop}
            onDragOver={(event) => event.preventDefault()}
          >
            {composerMode === "review_student_work" && (
              <div className="composer-mode">
                <ClipboardText size={16} />
                <div>
                  <strong>检查解法</strong>
                  <span>输入或粘贴你的解题步骤</span>
                </div>
                <button type="button" onClick={cancelReview} aria-label="退出检查解法">
                  <X size={15} />
                </button>
              </div>
            )}
            {attachment && (
              <div className="attachment-preview">
                <img src={attachment.url} alt="准备上传的题目图片" />
                <button type="button" onClick={removeAttachment} aria-label="移除图片">
                  <X size={15} weight="bold" />
                </button>
              </div>
            )}
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={onComposerKeyDown}
              placeholder={composerMode === "review_student_work"
                ? "输入你的解题步骤，或粘贴解答图片"
                : "输入问题，或直接粘贴题目图片"}
              rows={1}
              aria-label="输入问题"
              disabled={busy}
            />
            <div className="composer-toolbar">
              <label className="school-selector" title="按目标院校资料检索和出题">
                <span className="visually-hidden">目标院校</span>
                <select value={targetSchool} onChange={(event) => setTargetSchool(event.target.value)} disabled={busy}>
                  <option value="">通用题库</option>
                  {knowledgeSchools.map((school) => <option value={school} key={school}>{school}</option>)}
                </select>
              </label>
              <div className="answer-style-switch" role="group" aria-label="回答方式">
                {answerStyles.map((style) => (
                  <button
                    className={answerStyle === style.value ? "active" : ""}
                    type="button"
                    key={style.value}
                    title={style.title}
                    aria-pressed={answerStyle === style.value}
                    onClick={() => setAnswerStyle(style.value)}
                    disabled={busy || composerMode === "review_student_work"}
                  >
                    {style.label}
                  </button>
                ))}
              </div>
              <button
                className="attach-button"
                type="button"
                aria-label="上传题目图片"
                onClick={() => fileInputRef.current?.click()}
                disabled={busy}
              >
                <Paperclip size={20} />
              </button>
              <input
                ref={fileInputRef}
                className="visually-hidden"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={onFileChange}
              />
              <button
                className={busy ? "send-button stop-button" : "send-button"}
                type={busy ? "button" : "submit"}
                aria-label={busy ? "停止生成" : "发送"}
                title={busy ? "停止生成" : "发送"}
                onClick={busy ? stopResponse : undefined}
                disabled={!busy && !input.trim() && !attachment}
              >
                {busy ? <Stop size={16} weight="fill" /> : <ArrowUp size={19} weight="bold" />}
              </button>
            </div>
          </form>
          <p className="composer-note">SignalTutor 可能会出错，重要结论请结合教材复核。</p>
        </div>
      </section>

      {learningPanelOpen && (
        <>
          <button
            className="learning-backdrop"
            type="button"
            aria-label="关闭学习记录"
            onClick={() => {
              setLearningPanelOpen(false);
              setSelectedMistake(null);
              setMistakeImageUrl(null);
            }}
          />
          <aside className="learning-panel" aria-label="学习记录">
            <div className="learning-panel-header">
              <div>
                <strong>{selectedMistake ? "错题详情" : "学习记录"}</strong>
                <span>{selectedMistake ? "查看完整题目、原图与参考解析" : "错题与薄弱考点会按账号保存"}</span>
              </div>
              <button
                className="icon-control"
                type="button"
                aria-label="关闭学习记录"
                onClick={() => {
                  setLearningPanelOpen(false);
                  setSelectedMistake(null);
                  setMistakeImageUrl(null);
                }}
              >
                <X size={18} />
              </button>
            </div>

            {selectedMistake ? (
              <div className="mistake-detail">
                <button
                  className="mistake-back"
                  type="button"
                  onClick={() => {
                    setSelectedMistake(null);
                    setMistakeImageUrl(null);
                  }}
                >
                  <CaretLeft size={16} />
                  返回错题本
                </button>

                <div className="mistake-detail-meta">
                  <span>
                    {selectedMistake.source_type === "uploaded_image"
                      ? "上传题目"
                      : selectedMistake.source_type === "ai_generated"
                        ? "AI 生成题"
                        : "文字题目"}
                  </span>
                  <span>{chapterNames[selectedMistake.chapter] ?? selectedMistake.chapter}</span>
                </div>

                {mistakeImageLoading && (
                  <div className="mistake-image-loading">正在加载题目原图…</div>
                )}
                {mistakeImageUrl && (
                  <button
                    className="mistake-detail-image"
                    type="button"
                    onClick={() => setPreviewImageUrl(mistakeImageUrl)}
                    aria-label="放大查看错题原图"
                  >
                    <img src={mistakeImageUrl} alt="错题原图" />
                    <span>点击放大</span>
                  </button>
                )}

                <section className="mistake-detail-section">
                  <h2>题目</h2>
                  <MarkdownMath content={selectedMistake.question} />
                </section>

                <section className="mistake-detail-section">
                  <h2>参考解析</h2>
                  {selectedMistake.answer_markdown ? (
                    <MarkdownMath content={selectedMistake.answer_markdown} />
                  ) : (
                    <p className="mistake-no-answer">这是一道待练习题，点击“开始解答”让助手带你完成。</p>
                  )}
                </section>

                {selectedMistake.common_mistakes.length > 0 && (
                  <section className="mistake-detail-section mistake-detail-warnings">
                    <h2>关键易错点</h2>
                    <ul>
                      {selectedMistake.common_mistakes.map((item) => (
                        <li key={item}><MarkdownMath content={item} /></li>
                      ))}
                    </ul>
                  </section>
                )}

                <div className="mistake-detail-actions">
                  <button type="button" onClick={() => askMistakeAgain(selectedMistake.question)}>
                    <ArrowBendUpLeft size={16} />
                    {selectedMistake.answer_markdown ? "再次提问" : "开始解答"}
                  </button>
                  <button
                    type="button"
                    onClick={() => void toggleMistakeMastery(selectedMistake.id, !selectedMistake.mastered)}
                  >
                    <CheckCircle size={16} weight={selectedMistake.mastered ? "fill" : "regular"} />
                    {selectedMistake.mastered ? "取消已掌握" : "标记掌握"}
                  </button>
                </div>
              </div>
            ) : (
              <>
            <section className="learning-section">
              <h2>薄弱考点</h2>
              {learningOverview?.topics.length ? (
                <div className="mastery-list">
                  {learningOverview.topics.slice(0, 6).map((topic) => (
                    <div className="mastery-row" key={topic.topic}>
                      <div>
                        <strong>{topic.topic.replace("/", " / ")}</strong>
                        <span>{topic.attempts} 次记录</span>
                      </div>
                      <div className="mastery-actions">
                        <b>{Math.round(topic.mastery * 100)}%</b>
                        <button
                          type="button"
                          onClick={() => void practiceWeakTopic(topic.topic)}
                          disabled={busy}
                        >
                          <Sparkle size={14} />
                          练一题
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="learning-empty">完成解法批改后，这里会形成个人薄弱点。</p>
              )}
            </section>

            <section className="learning-section mistake-section">
              <h2>错题本</h2>
              {learningOverview?.mistakes.length ? (
                <div className="mistake-list">
                  {learningOverview.mistakes.map((mistake) => (
                    <article className={mistake.mastered ? "mistake-row mastered" : "mistake-row"} key={mistake.id}>
                      <div>
                        <strong>{mistake.question}</strong>
                        <span>{chapterNames[mistake.chapter] ?? mistake.chapter}</span>
                      </div>
                      <div className="mistake-actions">
                        <button type="button" className="mistake-open" onClick={() => void openMistake(mistake)}>
                          <BookBookmark size={16} weight="fill" />
                          打开题目
                        </button>
                        <button type="button" onClick={() => askMistakeAgain(mistake.question)}>
                          <ArrowBendUpLeft size={16} />
                          再次提问
                        </button>
                        <button
                          type="button"
                          onClick={() => void toggleMistakeMastery(mistake.id, !mistake.mastered)}
                        >
                          <CheckCircle size={16} weight={mistake.mastered ? "fill" : "regular"} />
                          {mistake.mastered ? "已掌握" : "标记掌握"}
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="learning-empty">还没有错题。可以从任意回答下方加入。</p>
              )}
            </section>
              </>
            )}
          </aside>
        </>
      )}

      {previewImageUrl && (
        <div
          className="image-lightbox"
          role="dialog"
          aria-modal="true"
          aria-label="题目图片预览"
          onClick={() => setPreviewImageUrl(null)}
        >
          <button
            className="image-lightbox-close"
            type="button"
            aria-label="关闭图片预览"
            onClick={() => setPreviewImageUrl(null)}
          >
            <X size={20} />
          </button>
          <img
            src={previewImageUrl}
            alt="放大的题目图片"
            onClick={(event) => event.stopPropagation()}
          />
        </div>
      )}
    </main>
  );
}
