from pathlib import Path

PROMPT_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    allowed = {
        "vision_parser",
        "classifier",
        "planner",
        "solver",
        "verifier",
        "tutor",
        "direct_tutor",
    }
    if name not in allowed:
        raise ValueError(f"Unknown prompt: {name}")
    return (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")
