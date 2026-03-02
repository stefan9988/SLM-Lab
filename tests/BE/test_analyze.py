"""Tests for document analysis endpoint helpers and extraction prompt."""

import json

import pytest

from BE.app import (
    validate_extraction_keys,
    _parse_extraction_json,
    _normalise_validation_results,
)
from AI.prompts.extraction_prompt import build_extraction_prompt

# --- validate_extraction_keys ---


class TestValidateExtractionKeys:
    def test_all_keys_present(self):
        schema_fields = [
            {"key": "name", "description": "Full name"},
            {"key": "email", "description": "Email address"},
        ]
        results = [
            {
                "key": "name",
                "extraction": "John",
                "location": {"page_num": 1, "chunk_num": None},
            },
            {"key": "email", "extraction": "j@x.com", "location": None},
        ]
        validated = validate_extraction_keys(results, schema_fields)
        keys = [r["key"] for r in validated]
        assert "name" in keys
        assert "email" in keys
        assert len(validated) == 2

    def test_missing_key_added_with_nulls(self):
        schema_fields = [
            {"key": "name", "description": ""},
            {"key": "phone", "description": ""},
        ]
        results = [
            {"key": "name", "extraction": "Alice", "location": None},
        ]
        validated = validate_extraction_keys(results, schema_fields)
        keys = [r["key"] for r in validated]
        assert "phone" in keys
        phone_row = next(r for r in validated if r["key"] == "phone")
        assert phone_row["extraction"] is None
        assert phone_row["location"] is None

    def test_numbered_variants_cover_base_key(self):
        schema_fields = [{"key": "phone_number", "description": ""}]
        results = [
            {"key": "phone_number_1", "extraction": "111", "location": None},
            {"key": "phone_number_2", "extraction": "222", "location": None},
        ]
        validated = validate_extraction_keys(results, schema_fields)
        keys = [r["key"] for r in validated]
        assert "phone_number_1" in keys
        assert "phone_number_2" in keys
        # Base key should NOT be added because numbered variants cover it
        assert "phone_number" not in keys

    def test_empty_string_extraction_becomes_none(self):
        schema_fields = [{"key": "x", "description": ""}]
        results = [{"key": "x", "extraction": "", "location": ""}]
        validated = validate_extraction_keys(results, schema_fields)
        assert validated[0]["extraction"] is None
        assert validated[0]["location"] is None

    def test_empty_results_adds_all_keys(self):
        schema_fields = [
            {"key": "a", "description": ""},
            {"key": "b", "description": ""},
        ]
        validated = validate_extraction_keys([], schema_fields)
        keys = {r["key"] for r in validated}
        assert keys == {"a", "b"}
        for r in validated:
            assert r["extraction"] is None
            assert r["location"] is None


# --- _parse_extraction_json ---


class TestParseExtractionJson:
    def test_plain_json_array(self):
        text = '[{"key": "name", "extraction": "Alice", "location": null}]'
        result = _parse_extraction_json(text)
        assert len(result) == 1
        assert result[0]["key"] == "name"

    def test_json_in_markdown_fences(self):
        text = '```json\n[{"key": "x", "extraction": "y", "location": null}]\n```'
        result = _parse_extraction_json(text)
        assert len(result) == 1
        assert result[0]["key"] == "x"

    def test_json_with_surrounding_text(self):
        text = 'Here are the results:\n[{"key": "a", "extraction": "b", "location": null}]\nDone.'
        result = _parse_extraction_json(text)
        assert result[0]["key"] == "a"

    def test_no_array_raises(self):
        with pytest.raises(ValueError, match="No JSON array found"):
            _parse_extraction_json("no json here")

    def test_empty_array(self):
        result = _parse_extraction_json("[]")
        assert result == []


# --- _normalise_validation_results ---


class TestNormaliseValidationResults:
    def test_valid_results_pass_through_unchanged(self):
        raw = [
            {
                "key": "company_name",
                "claim": "company_name: Acme",
                "validated_value": "Acme Corp",
                "status": "correct",
                "sources": ["https://example.com"],
            }
        ]
        result = _normalise_validation_results(raw)
        assert len(result) == 1
        assert result[0]["key"] == "company_name"
        assert result[0]["claim"] == "company_name: Acme"
        assert result[0]["validated_value"] == "Acme Corp"
        assert result[0]["status"] == "correct"
        assert result[0]["sources"] == ["https://example.com"]

    def test_missing_fields_get_defaults(self):
        raw = [{}]
        result = _normalise_validation_results(raw)
        assert len(result) == 1
        assert result[0]["key"] is None
        assert result[0]["claim"] == ""
        assert result[0]["validated_value"] is None
        assert result[0]["status"] == "not_found"
        assert result[0]["sources"] == []

    def test_invalid_status_coerced_to_not_found(self):
        raw = [{"key": "x", "claim": "x: y", "status": "unknown_status"}]
        result = _normalise_validation_results(raw)
        assert result[0]["status"] == "not_found"

    def test_all_valid_statuses_accepted(self):
        for status in ("correct", "incorrect", "not_found"):
            raw = [{"status": status}]
            result = _normalise_validation_results(raw)
            assert result[0]["status"] == status

    def test_non_dict_items_are_skipped(self):
        raw = ["a string", 42, None, {"key": "kept", "status": "correct"}]
        result = _normalise_validation_results(raw)
        assert len(result) == 1
        assert result[0]["key"] == "kept"

    def test_empty_string_fields_become_defaults(self):
        raw = [{"key": "", "claim": "", "validated_value": "", "sources": None}]
        result = _normalise_validation_results(raw)
        assert result[0]["key"] is None
        assert result[0]["claim"] == ""
        assert result[0]["validated_value"] is None
        assert result[0]["sources"] == []

    def test_empty_list_returns_empty(self):
        assert _normalise_validation_results([]) == []


# --- build_extraction_prompt ---


class TestBuildExtractionPrompt:
    def test_contains_file_id(self):
        prompt = build_extraction_prompt(
            [{"key": "name", "description": "Full name"}],
            "abc-123",
        )
        assert "abc-123" in prompt

    def test_contains_field_keys(self):
        fields = [
            {"key": "name", "description": "Full name"},
            {"key": "email", "description": "Email address"},
        ]
        prompt = build_extraction_prompt(fields, "file-1")
        assert "- name: Full name" in prompt
        assert "- email: Email address" in prompt

    def test_contains_json_instructions(self):
        prompt = build_extraction_prompt([{"key": "x", "description": ""}], "f")
        assert "JSON array" in prompt
        assert "ALL schema keys" in prompt
