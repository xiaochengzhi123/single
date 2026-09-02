const latexCommand = /\\(?:alpha|beta|cos|delta|frac|int|left|lim|omega|pi|right|sin|sqrt|sum|theta|times|to)\b/;

function dedent(block: string) {
  const lines = block.replace(/^\n+|\n+$/g, "").split("\n");
  const indents = lines
    .filter((line) => line.trim())
    .map((line) => line.match(/^[ \t]*/)?.[0].length ?? 0);
  const minimum = indents.length ? Math.min(...indents) : 0;
  return lines.map((line) => line.slice(minimum)).join("\n").trim();
}

function displayMath(body: string) {
  return `\n\n$$\n${dedent(body)}\n$$\n\n`;
}

export function normalizeMathMarkdown(content: string) {
  let normalized = content.replace(/\r\n?/g, "\n");

  normalized = normalized.replace(
    /```[^\n]*\n([\s\S]*?)```/g,
    (fence, body: string) => (
      latexCommand.test(body) || /[_^]\{[^}]+\}/.test(body)
        ? displayMath(body)
        : fence
    ),
  );

  normalized = normalized.replace(
    /^[ \t]*\$(?!\$)[ \t]*\n([\s\S]*?)\n[ \t]*\$(?!\$)[ \t]*$/gm,
    (_match, body: string) => displayMath(body),
  );

  normalized = normalized
    .replace(/\\\[/g, "\n\n$$\n")
    .replace(/\\\]/g, "\n$$\n\n")
    .replace(/\\\(/g, "$")
    .replace(/\\\)/g, "$");

  const lines = normalized.split("\n");
  let insideDisplayMath = false;
  normalized = lines.map((line) => {
    if (line.trim() === "$$") {
      insideDisplayMath = !insideDisplayMath;
      return "$$";
    }
    if (!insideDisplayMath && !line.includes("$") && latexCommand.test(line)) {
      const trimmed = line.trim();
      if (!/[\u3400-\u9fff]/.test(trimmed)) return displayMath(trimmed).trim();
    }
    return insideDisplayMath ? line.trimStart() : line;
  }).join("\n");

  return normalized
    .replace(/[ \t]*\$\$[ \t]*/g, () => "\n\n$$\n\n")
    .replace(/^\s*\$(?!\$)\s*$/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}
