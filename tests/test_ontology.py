from palantir_tw.ontology import EntityType, EvidenceGrade, Predicate


def test_evidence_grades_cover_a_to_e():
    assert [g.value for g in EvidenceGrade] == ["A", "B", "C", "D", "E"]


def test_core_entity_types():
    for t in ("person", "party", "district", "election", "document"):
        assert t in {e.value for e in EntityType}


def test_core_predicates():
    assert Predicate.DONATED_TO.value == "捐赠"
    assert Predicate.MEMBER_OF.value == "隶属政党"
