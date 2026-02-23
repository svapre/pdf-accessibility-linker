from data_models.schemas import TargetNode, SemanticReference


def test_target_node_requires_positive_page_number():
    try:
        TargetNode(
            target_id="chapter:01",
            target_type="hierarchy",
            exact_name="Intro",
            page_number=0,
        )
    except ValueError:
        return
    assert False, "Expected ValueError for page_number < 1"


def test_semantic_reference_accepts_valid_anchor_and_bbox():
    ref = SemanticReference(
        source_page=1,
        short_anchor="page:arabic:10",
        context_sentence="See page 10 for details.",
        source_bbox=(10.0, 20.0, 40.0, 30.0),
    )
    assert ref.short_anchor == "page:arabic:10"
