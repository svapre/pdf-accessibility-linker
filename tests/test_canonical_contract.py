from utils.canonical import CanonicalURN


def test_generate_and_parse_page_urn_round_trip():
    urn = CanonicalURN.generate_page_urn(42, "roman")
    num_type, value = CanonicalURN.parse_page_urn(urn)

    assert urn == "page:roman:42"
    assert num_type == "roman"
    assert value == 42


def test_slugify_produces_safe_namespace():
    assert CanonicalURN.slugify("Theme 1: Origins") == "theme-1-origins"
