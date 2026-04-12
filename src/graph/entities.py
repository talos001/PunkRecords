from dataclasses import dataclass, field
from typing import Dict, Optional, Any


@dataclass
class Entity:
    """Represents a knowledge graph entity (concept, note, person, etc.)."""

    id: str
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
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
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type,
            "properties": self.properties,
        }
