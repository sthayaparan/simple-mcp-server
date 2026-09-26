"""In-memory member data."""

from pydantic import BaseModel


class Member(BaseModel):
    """A member record."""

    name: str
    email: str
    mobile: str


MEMBERS: list[Member] = [
    Member(name="Fiona Johnson", email="fiona.johnson@example.com", mobile="+1-555-0101"),
    Member(name="Felix Smith", email="felix.smith@example.com", mobile="+1-555-0102"),
    Member(name="Faith Williams", email="faith.williams@example.com", mobile="+1-555-0103"),
    Member(name="Finn Brown", email="finn.brown@example.com", mobile="+1-555-0104"),
    Member(name="Freya Davis", email="freya.davis@example.com", mobile="+1-555-0105"),
    Member(name="Frank Miller", email="frank.miller@example.com", mobile="+1-555-0106"),
    Member(name="Flora Wilson", email="flora.wilson@example.com", mobile="+1-555-0107"),
    Member(name="Fred Moore", email="fred.moore@example.com", mobile="+1-555-0108"),
    Member(name="Farah Taylor", email="farah.taylor@example.com", mobile="+1-555-0109"),
    Member(name="Francis Anderson", email="francis.anderson@example.com", mobile="+1-555-0110"),
]
