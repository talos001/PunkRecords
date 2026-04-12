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
