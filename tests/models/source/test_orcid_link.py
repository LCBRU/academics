from academics.model.academic import Source


def test__source_orcid_link():
    s = Source(orcid="0000-0002-1825-0097")

    assert s.orcid_link == "https://orcid.org/0000-0002-1825-0097"


def test__source_orcid_link_none():
    s = Source(orcid=None)

    assert s.orcid is None
    assert s.orcid_link is None