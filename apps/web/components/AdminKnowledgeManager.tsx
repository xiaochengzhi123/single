"use client";

import {
  BookOpen,
  CheckCircle,
  Eye,
  EyeSlash,
  FileArrowUp,
  FileText,
  Trash,
  WarningCircle,
} from "@phosphor-icons/react";
import { FormEvent, useEffect, useState } from "react";

import {
  createKnowledgeEntry,
  deleteKnowledgeEntry,
  importKnowledgeFile,
  KnowledgeEntry,
  KnowledgeKind,
  listKnowledgeEntries,
  setKnowledgePublished,
} from "../lib/auth";

const kindNames: Record<KnowledgeKind, string> = {
  past_exam: "历年真题",
  textbook: "教材章节",
  formula: "常用公式",
  syllabus: "考试范围",
  solution: "标准解法",
  other: "其他资料",
};

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

export function AdminKnowledgeManager({ adminKey }: { adminKey: string }) {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [kind, setKind] = useState<KnowledgeKind>("past_exam");
  const [school, setSchool] = useState("");
  const [year, setYear] = useState("");
  const [chapter, setChapter] = useState("signals");
  const [topics, setTopics] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    void refresh();
  }, []);

  async function refresh() {
    try {
      setEntries(await listKnowledgeEntries(adminKey));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "知识库加载失败");
    }
  }

  function resetForm() {
    setTitle("");
    setContent("");
    setSchool("");
    setYear("");
    setTopics("");
    setDifficulty("");
    setSourceUrl("");
    setFile(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file && !content.trim()) {
      setError("请输入资料内容，或者选择一个资料文件");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      if (file) {
        const result = await importKnowledgeFile(adminKey, file, {
          title: title.trim(),
          kind,
          school: school.trim(),
          year,
          chapter,
          topics,
          difficulty,
          sourceUrl: sourceUrl.trim(),
        });
        setEntries((current) => [...result.entries, ...current]);
        setNotice(`导入完成，共新增 ${result.imported} 个可检索片段`);
      } else {
        const created = await createKnowledgeEntry(adminKey, {
          title: title.trim(),
          content: content.trim(),
          kind,
          school: school.trim() || null,
          year: year ? Number(year) : null,
          chapter,
          topics: topics.split(/[，,、]/).map((item) => item.trim()).filter(Boolean),
          difficulty: difficulty ? Number(difficulty) : null,
          source_page: null,
          source_url: sourceUrl.trim() || null,
          published: true,
        });
        setEntries((current) => [created, ...current]);
        setNotice("知识条目已经发布，学生提问时可以检索到它");
      }
      resetForm();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "资料保存失败");
    } finally {
      setBusy(false);
    }
  }

  async function togglePublished(entry: KnowledgeEntry) {
    setBusy(true);
    setError(null);
    try {
      const updated = await setKnowledgePublished(adminKey, entry.id, !entry.published);
      setEntries((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "更新发布状态失败");
    } finally {
      setBusy(false);
    }
  }

  async function remove(entry: KnowledgeEntry) {
    if (!window.confirm(`确定删除“${entry.title}”吗？此操作无法撤销。`)) return;
    setBusy(true);
    setError(null);
    try {
      await deleteKnowledgeEntry(adminKey, entry.id);
      setEntries((current) => current.filter((item) => item.id !== entry.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "删除知识条目失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="knowledge-admin-layout">
      <section className="knowledge-create" aria-labelledby="knowledge-create-title">
        <h1 id="knowledge-create-title">导入真题知识库</h1>
        <p>支持文字录入，或上传文字版 PDF、Markdown、TXT、JSON、JSONL。扫描版 PDF 请先进行 OCR。</p>
        <form className="knowledge-form" onSubmit={submit}>
          <label><span>资料名称</span><input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="例如：西电 2025 年信号与系统真题" required /></label>
          <div className="knowledge-form-grid">
            <label><span>资料类型</span><select value={kind} onChange={(event) => setKind(event.target.value as KnowledgeKind)}>{Object.entries(kindNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label><span>所属章节</span><select value={chapter} onChange={(event) => setChapter(event.target.value)}>{Object.entries(chapterNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label><span>学校（可选）</span><input value={school} onChange={(event) => setSchool(event.target.value)} placeholder="西安电子科技大学" /></label>
            <label><span>年份（可选）</span><input type="number" min="1980" max="2100" value={year} onChange={(event) => setYear(event.target.value)} placeholder="2025" /></label>
            <label><span>难度（可选）</span><select value={difficulty} onChange={(event) => setDifficulty(event.target.value)}><option value="">不设置</option>{[1, 2, 3, 4, 5].map((value) => <option value={value} key={value}>{value} 级</option>)}</select></label>
            <label><span>考点</span><input value={topics} onChange={(event) => setTopics(event.target.value)} placeholder="卷积，傅里叶变换" /></label>
          </div>
          <label><span>原始来源链接（可选）</span><input type="url" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="https://..." /></label>
          <label><span>直接录入内容</span><textarea value={content} onChange={(event) => setContent(event.target.value)} placeholder="粘贴完整题干、标准答案、教材摘要或公式说明。上传文件时可以留空。" rows={7} disabled={Boolean(file)} /></label>
          <label className="knowledge-file-input">
            <FileArrowUp size={20} />
            <span>{file ? file.name : "选择资料文件（最大 20MB）"}</span>
            <input type="file" accept=".pdf,.md,.markdown,.txt,.json,.jsonl,application/pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          </label>
          {file && <button className="knowledge-clear-file" type="button" onClick={() => setFile(null)}>取消文件，改为手工录入</button>}
          <button className="knowledge-submit" type="submit" disabled={busy}><BookOpen size={18} />{busy ? "正在处理" : file ? "导入并发布" : "保存并发布"}</button>
        </form>
        {notice && <p className="knowledge-notice"><CheckCircle size={17} />{notice}</p>}
        {error && <p className="auth-error" role="alert"><WarningCircle size={17} />{error}</p>}
      </section>

      <section className="knowledge-list-section" aria-labelledby="knowledge-list-title">
        <div className="admin-section-title">
          <div><h2 id="knowledge-list-title">已导入资料</h2><p>已发布条目会参与学生问答检索；下架后保留内容但不再参与回答。</p></div>
          <strong>{entries.length}</strong>
        </div>
        <div className="knowledge-list">
          {entries.map((entry) => (
            <article className={entry.published ? "knowledge-row" : "knowledge-row unpublished"} key={entry.id}>
              <span className="knowledge-row-icon"><FileText size={18} /></span>
              <div className="knowledge-row-main">
                <div className="knowledge-row-title"><strong>{entry.title}</strong><span>{kindNames[entry.kind]}</span></div>
                <p>{entry.content}</p>
                <div className="knowledge-row-meta">
                  {entry.school && <span>{entry.school}</span>}
                  {entry.year && <span>{entry.year} 年</span>}
                  <span>{chapterNames[entry.chapter] ?? entry.chapter}</span>
                  {entry.source_page && <span>第 {entry.source_page} 页</span>}
                  {entry.topics.slice(0, 3).map((topic) => <span key={topic}>{topic}</span>)}
                </div>
              </div>
              <div className="knowledge-row-actions">
                <button type="button" onClick={() => void togglePublished(entry)} disabled={busy}>{entry.published ? <EyeSlash size={16} /> : <Eye size={16} />}{entry.published ? "下架" : "发布"}</button>
                <button type="button" className="danger" onClick={() => void remove(entry)} disabled={busy}><Trash size={16} />删除</button>
              </div>
            </article>
          ))}
          {!entries.length && <div className="admin-empty"><BookOpen size={24} /><span>还没有导入资料</span></div>}
        </div>
      </section>
    </div>
  );
}
