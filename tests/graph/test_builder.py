from src.graph.builder import GraphBuilder
from src.graph.entities import Entity, Relation


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
