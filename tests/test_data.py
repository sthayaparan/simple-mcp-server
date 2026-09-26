"""Tests for the in-memory member data."""
# pylint: disable=missing-function-docstring

from member_mcp.data import MEMBERS


def test_has_ten_members():
    assert len(MEMBERS) == 10


def test_all_fields_populated():
    for member in MEMBERS:
        assert member.name
        assert member.email
        assert member.mobile


def test_names_unique():
    assert len({m.name for m in MEMBERS}) == len(MEMBERS)


def test_emails_unique_and_valid():
    emails = [m.email for m in MEMBERS]
    assert len(set(emails)) == len(emails)
    assert all("@" in e for e in emails)
