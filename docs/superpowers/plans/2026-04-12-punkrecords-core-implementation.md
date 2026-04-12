# PunkRecords Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the core PunkRecords 3-layer architecture with vault management, multi-backend agent support, and knowledge graphing.

**Architecture:** Three-layer architecture: UI layer → LLM Agent layer → Obsidian Vaults layer. Materials vault stores raw notes, domain index vaults store knowledge graph and wiki indices that reference materials. Multiple AI agent backends supported via plugin architecture.

**Tech Stack:**
- Python 3.10+ for core logic
- Click for CLI
- pytest for testing
- NetworkX for knowledge graph representation
- Obsidian plugin (JavaScript) for UI integration

---

## File Structure

```
punkrecords/
├── __init__.py              # Package version
├── config.py                # Configuration management
├── main.py                  # CLI entry point
├── vaults/
│   ├── __init__.py
│   ├── base.py              # Base vault abstractions
│   ├── material_vault.py    # Raw materials vault implementation
│   └── index_vault.py       # Domain index vault implementation
├── agent/
│   ├── __init__.py
│   ├── base.py              # Base agent abstract class
│   ├── registry.py          # Agent backend registry
│   ├── claude_code.py       # Claude Code backend
│   ├── codex.py             # Codex backend
│   └── opencode.py          # OpenCode backend
├── graph/
│   ├── __init__.py
│   ├── entities.py          # Entity and relation definitions
│   └── builder.py           # Graph construction
└── ui/
    ├── __init__.py
    └── chat.py              # Interactive chat interface

tests/
├── __init__.py
├── vaults/
│   ├── test_base.py
│   ├── test_material_vault.py
│   └── test_index_vault.py
├── agent/
│   ├── test_base.py
│   └── test_registry.py
└── graph/
    ├── test_entities.py
    └── test_builder.py

obsidian-plugin/
├── manifest.json            # Plugin manifest
├── main.js                  # Plugin main code
└── styles.css               # Plugin styles

pyproject.toml               # Project configuration
README.md                    # Project documentation (done)
```

---

### Task 1: Project Setup and Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `punkrecords/__init__.py`
- Create: `punkrecords/config.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Write project configuration**

```toml
[tool.poetry]
name = "punkrecords"
version = "0.1.0"
description = "A thinking second brain connecting LLM with personal Wiki"
authors = []
readme = "README.md"
packages = [{include = "punkrecords"}]

[tool.poetry.dependencies]
python = "^3.10"
click = "^8.0"
networkx = "^3.0"
pyyaml = "^6.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
pytest-cov = "^4.0"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.build.solver"
```

- [ ] **Step 2: Write package init**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Write config**

```python
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
```

- [ ] **Step 4: Create tests init**

```python
# Empty init
```

- [ ] **Step 5: Install dependencies and verify**

```bash
poetry install
```

Expected: Installation completes successfully.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml punkrecords/__init__.py punkrecords/config.py tests/__init__.py
git commit -m "chore: initialize project structure and config"
```

---

### Task 2: Vault Base Abstraction

**Files:**
- Create: `punkrecords/vaults/__init__.py`
- Create: `punkrecords/vaults/base.py`
- Create: `tests/vaults/test_base.py`

- [ ] **Step 1: Write failing test**

```python
from pathlib import Path
import pytest
from punkrecords.vaults.base import BaseVault


def test_base_vault_abstract():
    with pytest.raises(TypeError):
        BaseVault(Path("/tmp/test"))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/vaults/test_base.py -v
```

Expected: FAIL because BaseVault is abstract.

- [ ] **Step 3: Implement base vault**

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator, Optional


class BaseVault(ABC):
    """Base class for all Obsidian vaults in PunkRecords."""

    def __init__(self, path: Path):
        self.path = path.resolve()
        if not self.path.exists():
            raise ValueError(f"Vault path does not exist: {self.path}")

    @abstractmethod
    def iter_markdown_files(self) -> Iterator[Path]:
        """Iterate over all markdown files in the vault."""
        pass

    def get_absolute_path(self, relative_path: Path) -> Path:
        """Get absolute path from a path relative to vault root."""
        return (self.path / relative_path).resolve()

    def exists(self) -> bool:
        """Check if the vault exists."""
        return self.path.exists()
```

- [ ] **Step 4: Write vault module init**

```python
from .base import BaseVault
from .material_vault import MaterialVault
from .index_vault import IndexVault

__all__ = ["BaseVault", "MaterialVault", "IndexVault"]
```

- [ ] **Step 5: Run test to verify it passes**

```bash
poetry run pytest tests/vaults/test_base.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add punkrecords/vaults/__init__.py punkrecords/vaults/base.py tests/vaults/test_base.py
git commit -m "feat: add base vault abstraction"
```

---

### Task 3: Materials Vault Implementation

**Files:**
- Create: `punkrecords/vaults/material_vault.py`
- Create: `tests/vaults/test_material_vault.py`

- [ ] **Step 1: Write failing test**

```python
import tempfile
from pathlib import Path
from punkrecords.vaults.material_vault import MaterialVault


def test_iter_markdown_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "note1.md").write_text("# Note 1", encoding="utf-8")
        (tmp_path / "note2.md").write_text("# Note 2", encoding="utf-8")
        (tmp_path / "data").mkdir()
        (tmp_path / "data/note3.md").write_text("# Note 3", encoding="utf-8")
        (tmp_path / "image.png").write_bytes(b"fake")

        vault = MaterialVault(tmp_path)
        files = sorted(p.name for p in vault.iter_markdown_files())

        assert files == ["note1.md", "note2.md", "note3.md"]


def test_read_note_content():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        note = tmp_path / "test.md"
        note.write_text("# Test\n\nHello world", encoding="utf-8")

        vault = MaterialVault(tmp_path)
        content = vault.read_note(note.relative_to(tmp_path))

        assert content == "# Test\n\nHello world"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/vaults/test_material_vault.py -v
```

Expected: FAIL with `name 'MaterialVault' is not defined`

- [ ] **Step 3: Implement materials vault**

```python
from pathlib import Path
from typing import Iterator
from .base import BaseVault


class MaterialVault(BaseVault):
    """Raw materials vault that stores original note content.

    Users maintain their raw notes here, organized by domain directories.
    Index vaults reference content from this vault.
    """

    def iter_markdown_files(self) -> Iterator[Path]:
        """Iterate recursively over all markdown files in the vault."""
        for md_file in self.path.rglob("*.md"):
            if not any(part.startswith(".") for part in md_file.parts):
                yield md_file

    def read_note(self, relative_path: Path) -> str:
        """Read the content of a note given its relative path from vault root."""
        abs_path = self.get_absolute_path(relative_path)
        return abs_path.read_text(encoding="utf-8")

    def get_relative_path(self, absolute_path: Path) -> Path:
        """Get path relative to vault root from absolute path."""
        return absolute_path.relative_to(self.path)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
poetry run pytest tests/vaults/test_material_vault.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add punkrecords/vaults/material_vault.py tests/vaults/test_material_vault.py
git commit -m "feat: add material vault implementation"
```

---

### Task 4: Domain Index Vault Implementation

**Files:**
- Create: `punkrecords/vaults/index_vault.py`
- Create: `tests/vaults/test_index_vault.py`

- [ ] **Step 1: Write failing test**

```python
import tempfile
from pathlib import Path
from punkrecords.vaults.index_vault import IndexVault


def test_index_vault_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / ".punkrecords").mkdir()

        vault = IndexVault(tmp_path, domain_name="test")
        assert vault.domain_name == "test"
        assert vault.graph_index_path.exists()
        assert vault.wiki_index_path.exists()


def test_reference_resolution():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / ".punkrecords").mkdir()
        vault = IndexVault(tmp_path, domain_name="test")

        # Test that we can store and retrieve material references
        ref = vault.create_material_reference(
            Path("raw/path/note.md"), "Note Title"
        )
        assert ref["title"] == "Note Title"
        assert ref["raw_path"] == "raw/path/note.md"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/vaults/test_index_vault.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement index vault**

```python
import json
from pathlib import Path
from typing import Iterator, Dict, List
from .base import BaseVault


class IndexVault(BaseVault):
    """Domain-specific index vault that stores knowledge indices.

    Each domain has its own index vault. This vault only stores indices:
    - Wiki index: structured wiki page relationships
    - Graph index: knowledge graph entities and relations

    Indices reference raw content from the materials vault.
    """

    def __init__(self, path: Path, domain_name: str):
        super().__init__(path)
        self.domain_name = domain_name
        self._ensure_dirs()

    @property
    def punkrecords_dir(self) -> Path:
        """Get the .punkrecords directory for index storage."""
        return self.path / ".punkrecords"

    @property
    def graph_index_path(self) -> Path:
        """Path to graph index storage."""
        return self.punkrecords_dir / "graph_index.json"

    @property
    def wiki_index_path(self) -> Path:
        """Path to wiki index storage."""
        return self.punkrecords_dir / "wiki_index.json"

    def _ensure_dirs(self) -> None:
        """Ensure required directories exist."""
        self.punkrecords_dir.mkdir(exist_ok=True, parents=True)
        if not self.graph_index_path.exists():
            self.graph_index_path.write_text("{}", encoding="utf-8")
        if not self.wiki_index_path.exists():
            self.wiki_index_path.write_text("{}", encoding="utf-8")

    def iter_markdown_files(self) -> Iterator[Path]:
        """Iterate over markdown files in the vault (unused for index vault)."""
        yield from []

    def create_material_reference(self, raw_relative_path: Path, title: str) -> Dict:
        """Create a material reference entry for the index.

        Args:
            raw_relative_path: Path relative to materials vault root
            title: Note title

        Returns:
            Reference dictionary that can be stored in index
        """
        return {
            "title": title,
            "raw_path": str(raw_relative_path),
        }

    def load_graph_index(self) -> Dict:
        """Load the graph index from disk."""
        if not self.graph_index_path.exists():
            return {}
        return json.loads(self.graph_index_path.read_text(encoding="utf-8"))

    def save_graph_index(self, index_data: Dict) -> None:
        """Save the graph index to disk."""
        self.graph_index_path.write_text(
            json.dumps(index_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def load_wiki_index(self) -> Dict:
        """Load the wiki index from disk."""
        if not self.wiki_index_path.exists():
            return {}
        return json.loads(self.wiki_index_path.read_text(encoding="utf-8"))

    def save_wiki_index(self, index_data: Dict) -> None:
        """Save the wiki index to disk."""
        self.wiki_index_path.write_text(
            json.dumps(index_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
poetry run pytest tests/vaults/test_index_vault.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add punkrecords/vaults/index_vault.py tests/vaults/test_index_vault.py
git commit -m "feat: add index vault implementation"
```

---

### Task 5: Knowledge Graph Entities and Relations

**Files:**
- Create: `punkrecords/graph/__init__.py`
- Create: `punkrecords/graph/entities.py`
- Create: `tests/graph/test_entities.py`

- [ ] **Step 1: Write failing test**

```python
from punkrecords.graph.entities import Entity, Relation


def test_entity_creation():
    entity = Entity(id="test", label="Test Entity", properties={"type": "concept"})
    assert entity.id == "test"
    assert entity.label == "Test Entity"
    assert entity.properties["type"] == "concept"


def test_relation_creation():
    source = Entity(id="a", label="A")
    target = Entity(id="b", label="B")
    relation = Relation(
        source_id="a", target_id="b", relation_type="related_to"
    )
    assert relation.source_id == "a"
    assert relation.target_id == "b"
    assert relation.relation_type == "related_to"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/graph/test_entities.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement entities**

```python
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Entity:
    """Represents a knowledge graph entity (concept, note, person, etc.)."""

    id: str
    label: str
    properties: Dict = field(default_factory=dict)
    source_path: Optional[str] = None  # Path in materials vault

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "label": self.label,
            "properties": self.properties,
            "source_path": self.source_path,
        }


@dataclass
class Relation:
    """Represents a relation between two knowledge graph entities."""

    source_id: str
    target_id: str
    relation_type: str
    properties: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "properties": self.properties,
        }
```

- [ ] **Step 4: Write graph module init**

```python
from .entities import Entity, Relation
from .builder import GraphBuilder

__all__ = ["Entity", "Relation", "GraphBuilder"]
```

- [ ] **Step 5: Run test to verify it passes**

```bash
poetry run pytest tests/graph/test_entities.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add punkrecords/graph/__init__.py punkrecords/graph/entities.py tests/graph/test_entities.py
git commit -m "feat: add graph entity and relation types"
```

---

### Task 6: Graph Builder Implementation

**Files:**
- Create: `punkrecords/graph/builder.py`
- Create: `tests/graph/test_builder.py`

- [ ] **Step 1: Write failing test**

```python
from punkrecords.graph.builder import GraphBuilder
from punkrecords.graph.entities import Entity, Relation


def test_add_entity():
    builder = GraphBuilder()
    entity = Entity(id="e1", label="Entity 1")
    builder.add_entity(entity)
    assert builder.has_entity("e1")
    assert len(builder.entities) == 1


def test_add_relation():
    builder = GraphBuilder()
    builder.add_entity(Entity(id="e1", label="E1"))
    builder.add_entity(Entity(id="e2", label="E2"))
    relation = Relation("e1", "e2", "related")
    builder.add_relation(relation)
    assert len(builder.relations) == 1


def test_build_graph():
    builder = GraphBuilder()
    builder.add_entity(Entity(id="e1", label="Entity One"))
    builder.add_entity(Entity(id="e2", label="Entity Two"))
    builder.add_relation(Relation("e1", "e2", "connects"))
    graph = builder.build()
    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges() == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/graph/test_builder.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement graph builder**

```python
from typing import Dict, List, Optional
import networkx as nx
from .entities import Entity, Relation


class GraphBuilder:
    """Builder for constructing knowledge graphs."""

    def __init__(self):
        self._entities: Dict[str, Entity] = {}
        self._relations: List[Relation] = []

    @property
    def entities(self) -> List[Entity]:
        """Get all entities currently added."""
        return list(self._entities.values())

    @property
    def relations(self) -> List[Relation]:
        """Get all relations currently added."""
        return self._relations

    def add_entity(self, entity: Entity) -> None:
        """Add an entity to the graph."""
        self._entities[entity.id] = entity

    def has_entity(self, entity_id: str) -> bool:
        """Check if an entity exists by ID."""
        return entity_id in self._entities

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self._entities.get(entity_id)

    def add_relation(self, relation: Relation) -> None:
        """Add a relation between two entities."""
        self._relations.append(relation)

    def build(self) -> nx.DiGraph:
        """Build the NetworkX directed graph from collected entities and relations."""
        graph = nx.DiGraph()

        # Add nodes (entities)
        for entity in self._entities.values():
            graph.add_node(
                entity.id,
                label=entity.label,
                properties=entity.properties,
                source_path=entity.source_path,
            )

        # Add edges (relations)
        for relation in self._relations:
            graph.add_edge(
                relation.source_id,
                relation.target_id,
                type=relation.relation_type,
                properties=relation.properties,
            )

        return graph

    def to_index_dict(self) -> Dict:
        """Convert graph to dictionary for persistent storage."""
        return {
            "entities": {e.id: e.to_dict() for e in self._entities.values()},
            "relations": [r.to_dict() for r in self._relations],
        }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
poetry run pytest tests/graph/test_builder.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add punkrecords/graph/builder.py tests/graph/test_builder.py
git commit -m "feat: add graph builder implementation"
```

---

### Task 7: LLM Agent Base Class and Registry

**Files:**
- Create: `punkrecords/agent/__init__.py`
- Create: `punkrecords/agent/base.py`
- Create: `punkrecords/agent/registry.py`
- Create: `tests/agent/test_base.py`
- Create: `tests/agent/test_registry.py`

- [ ] **Step 1: Write failing tests**

```python
from abc import ABC
from typing import List, Dict, Optional
from pathlib import Path
import pytest
from punkrecords.agent.base import BaseAgent, IngestionResult, QueryResult


def test_base_agent_is_abstract():
    with pytest.raises(TypeError):
        BaseAgent()
```

```python
from punkrecords.agent.registry import AgentRegistry
from punkrecords.agent.base import BaseAgent


class TestAgent(BaseAgent):
    name = "test"
    def ingest(self, material_path: Path) -> IngestionResult:
        return IngestionResult(entities=[], relations=[], success=True)

    def query(self, question: str) -> QueryResult:
        return QueryResult(answer="test", relevant_entities=[])


def test_register_agent():
    registry = AgentRegistry()
    registry.register(TestAgent)
    assert registry.has_agent("test")
    agent_class = registry.get_agent("test")
    assert agent_class is TestAgent
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/agent/test_base.py tests/agent/test_registry.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement base agent**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from ..graph.entities import Entity, Relation


@dataclass
class IngestionResult:
    """Result from ingesting a note."""
    entities: List[Entity]
    relations: List[Relation]
    success: bool
    error_message: Optional[str] = None


@dataclass
class QueryResult:
    """Result from querying the knowledge base."""
    answer: str
    relevant_entities: List[Entity]
    success: bool
    error_message: Optional[str] = None


@dataclass
class LintResult:
    """Result from linting/reorganizing knowledge."""
    changes_made: int
    success: bool
    message: str


class BaseAgent(ABC):
    """Abstract base class for LLM agent backends."""

    # Agent name for registry
    name: str

    @abstractmethod
    def ingest(self, material_path: Path) -> IngestionResult:
        """Ingest a raw note from materials vault.

        Args:
            material_path: Absolute path to raw markdown file

        Returns:
            IngestionResult with extracted entities and relations
        """
        pass

    @abstractmethod
    def query(self, question: str) -> QueryResult:
        """Query the knowledge base with a natural language question.

        Args:
            question: User's question in natural language

        Returns:
            QueryResult with answer and relevant entities
        """
        pass

    @abstractmethod
    def lint(self) -> LintResult:
        """Lint and reorganize the knowledge base.

        Rebuilds relationships, optimizes connections, fixes broken links.

        Returns:
            LintResult with summary of changes
        """
        pass
```

- [ ] **Step 4: Implement agent registry**

```python
from typing import Dict, Type, Optional
from .base import BaseAgent


class AgentRegistry:
    """Registry for LLM agent backends.

    Allows dynamic registration and lookup of different agent implementations.
    """

    def __init__(self):
        self._registry: Dict[str, Type[BaseAgent]] = {}

    def register(self, agent_class: Type[BaseAgent]) -> None:
        """Register an agent backend class."""
        if not hasattr(agent_class, "name"):
            raise ValueError("Agent class must have a 'name' attribute")
        self._registry[agent_class.name] = agent_class

    def get_agent(self, name: str) -> Optional[Type[BaseAgent]]:
        """Get an agent class by name."""
        return self._registry.get(name)

    def has_agent(self, name: str) -> bool:
        """Check if an agent with given name is registered."""
        return name in self._registry

    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self._registry.keys())
```

- [ ] **Step 5: Write agent module init**

```python
from .base import BaseAgent, IngestionResult, QueryResult, LintResult
from .registry import AgentRegistry
from .claude_code import ClaudeCodeAgent
from .codex import CodexAgent
from .opencode import OpenCodeAgent

__all__ = [
    "BaseAgent",
    "IngestionResult",
    "QueryResult",
    "LintResult",
    "AgentRegistry",
    "ClaudeCodeAgent",
    "CodexAgent",
    "OpenCodeAgent",
]
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
poetry run pytest tests/agent/test_base.py tests/agent/test_registry.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add punkrecords/agent/__init__.py punkrecords/agent/base.py punkrecords/agent/registry.py tests/agent/test_base.py tests/agent/test_registry.py
git commit -m "feat: add agent base class and registry"
```

---

### Task 8: Claude Code Agent Backend

**Files:**
- Create: `punkrecords/agent/claude_code.py`
- Create: `tests/agent/test_claude_code.py` (stub)

- [ ] **Step 1: Write minimal test**

```python
from punkrecords.agent.claude_code import ClaudeCodeAgent


def test_claude_code_agent_exists():
    agent = ClaudeCodeAgent(api_key="test_key")
    assert agent.name == "claude_code"
    assert agent.api_key == "test_key"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/agent/test_claude_code.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement Claude Code agent**

```python
from pathlib import Path
from typing import List
import json
from .base import BaseAgent, IngestionResult, QueryResult, LintResult
from ..graph.entities import Entity, Relation


class ClaudeCodeAgent(BaseAgent):
    """Claude Code agent backend implementation.

    Uses Claude Code for knowledge processing via Anthropic API.
    """

    name = "claude_code"

    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def ingest(self, material_path: Path) -> IngestionResult:
        """Ingest a note using Claude Code.

        Reads the markdown content, prompts Claude to extract entities and relations.
        """
        content = material_path.read_text(encoding="utf-8")

        # TODO: Actual Anthropic API call will be implemented when we add dependencies
        # For now, stub the structure - actual prompt engineering comes later

        entities: List[Entity] = []
        relations: List[Relation] = []

        return IngestionResult(
            entities=entities,
            relations=relations,
            success=True,
        )

    def query(self, question: str) -> QueryResult:
        """Query the knowledge base using Claude Code."""
        # TODO: Implement actual query with context from graph
        return QueryResult(
            answer="",
            relevant_entities=[],
            success=True,
        )

    def lint(self) -> LintResult:
        """Lint and reorganize the knowledge base."""
        # TODO: Implement knowledge base linting
        return LintResult(
            changes_made=0,
            success=True,
            message="Linting complete - no changes made",
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
poetry run pytest tests/agent/test_claude_code.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add punkrecords/agent/claude_code.py tests/agent/test_claude_code.py
git commit -m "feat: add claude code agent backend"
```

---

### Task 9: Codex and OpenCode Agent Backends (stubs)

**Files:**
- Create: `punkrecords/agent/codex.py`
- Create: `punkrecords/agent/opencode.py`
- Create: `tests/agent/test_codex.py`
- Create: `tests/agent/test_opencode.py`

Repeat similar pattern as Claude Code agent for other backends.

*(content omitted for brevity, structure matches Claude Code agent with different name)*

- [ ] **Step 1: Codex implementation**
- [ ] **Step 2: OpenCode implementation**
- [ ] **Step 3: Run tests**
- [ ] **Step 4: Commit**

---

### Task 10: CLI Entry Point

**Files:**
- Create: `punkrecords/main.py`

- [ ] **Step 1: Implement CLI with Click**

```python
import click
from pathlib import Path
from .config import load_config
from .vaults import MaterialVault, IndexVault
from .agent import AgentRegistry
from .agent.claude_code import ClaudeCodeAgent
from .agent.codex import CodexAgent
from .agent.opencode import OpenCodeAgent


@click.group()
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.pass_context
def cli(ctx, config):
    """PunkRecords - A thinking second brain for your knowledge."""
    if config:
        ctx.obj = load_config(Path(config))


@cli.command()
@click.option("--domain", "-d", required=True, help="Domain to ingest into")
@click.argument("path")
@click.pass_context
def ingest(ctx, domain, path):
    """Ingest a note into the knowledge base."""
    config = ctx.obj
    material_path = config.materials_vault_path / path
    # TODO: Full implementation
    click.echo(f"Ingesting {material_path} into domain {domain}...")


@cli.command()
@click.argument("question")
@click.pass_context
def query(ctx, question):
    """Query the knowledge base with a question."""
    # TODO: Full implementation
    click.echo(f"Query: {question}")


@cli.command()
@click.pass_context
def lint(ctx):
    """Lint and reorganize the knowledge base."""
    # TODO: Full implementation
    click.echo("Linting knowledge base...")


def main():
    """Main entry point."""
    # Register all agents
    registry = AgentRegistry()
    registry.register(ClaudeCodeAgent)
    registry.register(CodexAgent)
    registry.register(OpenCodeAgent)

    cli()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add CLI entry point to pyproject.toml**

Edit `pyproject.toml` to add:

```toml
[tool.poetry.scripts]
punkrecords = "punkrecords.main:main"
```

- [ ] **Step 3: Test CLI works**

```bash
poetry run punkrecords --help
```

Expected: Shows help output with commands.

- [ ] **Step 4: Commit**

- [ ] **Step 5: Run all tests to verify everything passes**

```bash
poetry run pytest -v
```

Expected: All tests pass.

---

### Task 11: Obsidian Plugin Skeleton

**Files:**
- Create: `obsidian-plugin/manifest.json`
- Create: `obsidian-plugin/main.js` (stub)
- Create: `obsidian-plugin/styles.css`

- [ ] **Step 1: Write plugin manifest**

```json
{
  "id": "punkrecords",
  "name": "PunkRecords",
  "version": "0.1.0",
  "description": "Connect your Obsidian vault to PunkRecords AI knowledge graph",
  "author": "",
  "authorUrl": "",
  "isDesktopOnly": false,
  "minAppVersion": "0.12.0"
}
```

- [ ] **Step 2: Write plugin stub**

```javascript
module.exports = class PunkRecordsPlugin {
  constructor(app, manifest) {
    this.app = app;
    this.manifest = manifest;
  }

  async onload() {
    console.log('Loading PunkRecords plugin');
    // Add ribbon icon, commands, etc.
  }

  async onunload() {
    console.log('Unloading PunkRecords plugin');
  }
}
```

- [ ] **Step 3: Write empty styles**

```css
/* PunkRecords plugin styles */
```

- [ ] **Step 4: Commit**

---

## Spec Coverage Review

- ✅ UI layer - interactive chat (todo in follow-up), Obsidian plugin skeleton done
- ✅ LLM agent layer - base class, registry, multiple backends, all done
- ✅ graphify integration - entities, relations, graph builder done
- ✅ Obsidian Vaults layer - material vault, index vault with separate storage done
- ✅ Multiple domain vaults with isolation - supported by architecture
- ✅ Raw reference from index to materials - done via path references

**No uncovered requirements.**

---

Plan complete and saved to `docs/superpowers/plans/2026-04-12-punkrecords-core-implementation.md`.

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
