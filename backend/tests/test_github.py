import pytest
from app.services.github_service import extract_username, fetch_github_profile_data
from app.security.sanitizer import validate_github_username

def test_extract_username_formats():
    assert extract_username("https://github.com/torvalds") == "torvalds"
    assert extract_username("https://github.com/octocat/repo") == "octocat"
    assert extract_username("@rahul-sharma") == "rahul-sharma"
    assert extract_username("rahulsharma123") == "rahulsharma123"
    assert extract_username("") is None

def test_validate_github_username():
    assert validate_github_username("octocat") is True
    assert validate_github_username("rahul-sharma-2026") is True
    assert validate_github_username("invalid..username") is False
    assert validate_github_username("") is False

@pytest.mark.asyncio
async def test_fetch_github_invalid_username():
    res = await fetch_github_profile_data("invalid@user!@#$")
    assert "error" in res
