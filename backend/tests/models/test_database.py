"""The Postgres URL always lands on the driver we ship (psycopg2)."""
import pytest

from models.database import pin_psycopg2_driver

NEON = "neondb_owner:secret@ep-x.eu-west-2.aws.neon.tech/neondb?sslmode=require"


@pytest.mark.parametrize("scheme", ["postgresql", "postgres", "postgresql+psycopg"])
def test_postgres_urls_are_pinned_to_psycopg2(scheme):
    assert pin_psycopg2_driver(f"{scheme}://{NEON}") == f"postgresql+psycopg2://{NEON}"


def test_credentials_and_query_params_survive():
    pinned = pin_psycopg2_driver(f"postgresql+psycopg://{NEON}")
    assert pinned.endswith(NEON)


@pytest.mark.parametrize("url", ["sqlite://", "sqlite:///./test.db", "not-a-url"])
def test_non_postgres_urls_are_untouched(url):
    assert pin_psycopg2_driver(url) == url
