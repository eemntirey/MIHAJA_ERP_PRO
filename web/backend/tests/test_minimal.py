"""Test minimaliste sans fixture DB pour diagnostiquer le hang pytest."""


def test_trivial():
    assert 1 + 1 == 2
