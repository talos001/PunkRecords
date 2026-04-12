"""Knowledge Graph module for PunkRecords.

Provides core entity and relation dataclasses for building knowledge graphs
from music production materials and research notes.
"""

from .entities import Entity, Relation
from .builder import GraphBuilder

__all__ = ["Entity", "Relation", "GraphBuilder"]
