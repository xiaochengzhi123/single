import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import { normalizeMathMarkdown } from "../lib/math-markdown";

export function MarkdownMath({ content }: { content: string }) {
  return (
    <div className="markdown-answer">
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[[rehypeKatex, { strict: false, throwOnError: false }]]}
      >
        {normalizeMathMarkdown(content)}
      </ReactMarkdown>
    </div>
  );
}
