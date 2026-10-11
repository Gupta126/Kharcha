from pathlib import Path


def get_prompt_path(prompt_name: str) -> Path:
    """Return path to prompt template, checking backend/app/llm/prompts then contracts/prompts."""
    current_dir = Path(__file__).resolve().parent
    local_path = current_dir / f"{prompt_name}.md"
    if local_path.exists():
        return local_path

    # Fallback to contracts/prompts
    repo_root = current_dir.parents[3]
    contract_path = repo_root / "contracts" / "prompts" / f"{prompt_name}.md"
    if contract_path.exists():
        return contract_path

    raise FileNotFoundError(f"Prompt template {prompt_name} not found")


def load_prompt(prompt_name: str, **kwargs: str) -> str:
    """Load a markdown prompt template and substitute format variables."""
    path = get_prompt_path(prompt_name)
    content = path.read_text(encoding="utf-8")
    for key, value in kwargs.items():
        content = content.replace(f"{{{{{key}}}}}", str(value))
    return content
