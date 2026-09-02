from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    success: bool
    tool_name: str
    evidence_id: str
    result_text: str | None = None
    result_latex: str | None = None
    metadata: dict = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
