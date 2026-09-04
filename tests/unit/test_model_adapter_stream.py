from signaltutor.agents.model_adapter import _partial_json_string_field


def test_partial_json_string_field_decodes_streamed_markdown() -> None:
    partial = '{"answer_markdown":"第一步：列出公式\\n然后计算 \\u03c9'

    assert _partial_json_string_field(partial, "answer_markdown") == "第一步：列出公式\n然后计算 ω"


def test_partial_json_string_field_waits_for_incomplete_escape() -> None:
    partial = '{"answer_markdown":"结果为 \\u03'

    assert _partial_json_string_field(partial, "answer_markdown") == "结果为 "
