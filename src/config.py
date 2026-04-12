from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any
import yaml


@dataclass
class Config:
    materials_vault_path: Path
    domain_index_paths: Dict[str, Path]
    default_agent_backend: str
    agent_api_key: Optional[str] = None


def load_config(config_path: Path) -> Config:
    """Load configuration from YAML file."""
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return Config(
        materials_vault_path=Path(data["materials_vault_path"]).expanduser(),
        domain_index_paths={
            k: Path(v).expanduser() for k, v in data["domain_index_paths"].items()
        },
        default_agent_backend=data.get("default_agent_backend", "claude_code"),
        agent_api_key=data.get("agent_api_key"),
    )
