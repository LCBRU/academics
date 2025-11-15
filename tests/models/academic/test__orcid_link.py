from academics.model.academic import Academic


def test__orcid_link_with_id():
    a = Academic(orcid="0000-0002-1825-0097")

    assert a.orcid is not None
    assert a.orcid_link == "https://orcid.org/0000-0002-1825-0097"


def test__orcid_link_none_returns_register():
    a = Academic(orcid=None)

    assert a.orcid is None
    assert a.orcid_link == "https://orcid.org/register"
