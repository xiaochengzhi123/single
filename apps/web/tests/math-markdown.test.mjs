import assert from "node:assert/strict";
import test from "node:test";

import { normalizeMathMarkdown } from "../lib/math-markdown.ts";


test("keeps valid display-math delimiters intact", () => {
  const result = normalizeMathMarkdown("结论：\n\n$$\nh[n]=\\delta[n]\n$$");

  assert.equal(result, "结论：\n\n$$\n\nh[n]=\\delta[n]\n\n$$");
});

test("repairs single-dollar display blocks and indentation", () => {
  const result = normalizeMathMarkdown(
    "$\n\n    h[n] = \\delta[n] + \\alpha \\delta[n-1]\n\n$",
  );

  assert.equal(
    result,
    "$$\n\nh[n] = \\delta[n] + \\alpha \\delta[n-1]\n\n$$",
  );
});

test("turns fenced LaTeX into rendered display math", () => {
  const result = normalizeMathMarkdown(
    "```latex\nS(e^{j\\omega}) = \\frac{1}{T}X(j\\omega/T)\n```",
  );

  assert.equal(
    result,
    "$$\n\nS(e^{j\\omega}) = \\frac{1}{T}X(j\\omega/T)\n\n$$",
  );
});
