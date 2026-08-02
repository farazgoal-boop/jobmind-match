"""Unit tests for app.services.cv_parser text-extraction helpers."""
from app.services.cv_parser import extract_sections, extract_technologies


def test_extract_technologies_matches_whole_words_only():
    text = "Built APIs with SQL and PostgreSQL, deployed via Docker on AWS."
    tech = extract_technologies(text)
    assert "sql" in tech
    assert "postgresql" in tech
    assert "docker" in tech
    assert "aws" in tech


def test_extract_technologies_no_false_positive_on_substring():
    # "sql" must not match inside an unrelated word like "visqlate"
    text = "Worked at a company called Visqlateworks on unrelated tooling."
    tech = extract_technologies(text)
    assert "sql" not in tech


def test_extract_technologies_empty_text_returns_empty_list():
    assert extract_technologies("") == []


def test_extract_sections_finds_experience_block():
    text = "Summary\n\nWork Experience\nSenior Developer at Acme Corp, 2019-2023.\n\nEducation\nBSc Computer Science."
    sections = extract_sections(text)
    assert "developer at acme corp" in sections["work_experience"]
    assert "computer science" in sections["education"]


def test_extract_sections_missing_markers_return_empty_strings():
    sections = extract_sections("Just a random paragraph with no headers at all.")
    assert sections == {"work_experience": "", "education": "", "projects": ""}
