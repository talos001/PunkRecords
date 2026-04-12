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
