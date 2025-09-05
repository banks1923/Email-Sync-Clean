"""Comprehensive test suite for input validation layer.

Tests cover:
- Parameter validation for search() and find_literal()
- Edge cases and error conditions
- Type coercion and clamping
- Date format validation
- Filter validation
- Unicode and fuzz testing
"""

import pytest
import string
import random
from datetime import datetime
from typing import Any

from lib.validators import (
    validate_search_params,
    validate_literal_search_params,
    _validate_query,
    _validate_limit,
    _validate_filters,
    _validate_fields,
    _validate_date_filter,
    _validate_source_type_filter,
    _remove_control_characters,
)
from lib.exceptions import ValidationError


class TestSearchParamValidation:
    """Test validate_search_params function."""
    
    @pytest.mark.parametrize("query,expected", [
        ("valid query", "valid query"),
        ("  spaces  ", "spaces"),
        ("unicode: ñ漢字🎉", "unicode: ñ漢字🎉"),
        ("multi\nline", "multi\nline"),
    ])
    def test_valid_queries(self, query: str, expected: str):
        """Test valid query inputs."""
        validated_query, _, _ = validate_search_params(query)
        assert validated_query == expected
    
    @pytest.mark.parametrize("query", [
        None,
        "",
        "   ",
        "\t\n",
        [],
        {},
        123,  # Will be coerced to "123"
    ])
    def test_invalid_queries(self, query: Any):
        """Test invalid query inputs."""
        if query == 123:  # Numbers get coerced to strings
            result, _, _ = validate_search_params(query)
            assert result == "123"
        else:
            with pytest.raises(ValidationError) as exc_info:
                validate_search_params(query)
            assert "query" in str(exc_info.value).lower()
    
    @pytest.mark.parametrize("limit,expected", [
        (10, 10),
        (1, 1),
        (200, 200),
        (0, 1),  # Clamped to min
        (-5, 1),  # Clamped to min
        (500, 200),  # Clamped to max
        ("50", 50),  # String coercion
        (50.7, 50),  # Float coercion
    ])
    def test_limit_validation(self, limit: Any, expected: int):
        """Test limit parameter validation and clamping."""
        _, validated_limit, _ = validate_search_params("test", limit)
        assert validated_limit == expected
    
    @pytest.mark.parametrize("limit", [
        "not_a_number",
        [],
        {},
        None,
        "10.5.2",
    ])
    def test_invalid_limits(self, limit: Any):
        """Test invalid limit values that can't be coerced."""
        with pytest.raises(ValidationError) as exc_info:
            validate_search_params("test", limit)
        assert "limit" in str(exc_info.value).lower()
    
    def test_filters_validation(self):
        """Test filter dictionary validation."""
        filters = {
            "date_from": "2024-01-01",
            "date_to": "2024-12-31T23:59:59Z",
            "source_type": "email",
            "party": "John Doe",
            "tags": ["legal", "contract"],
        }
        _, _, validated_filters = validate_search_params("test", 10, filters)
        assert validated_filters == filters
    
    def test_invalid_filter_type(self):
        """Test non-dict filter input."""
        with pytest.raises(ValidationError) as exc_info:
            validate_search_params("test", 10, "not_a_dict")
        assert "dictionary" in str(exc_info.value).lower()
    
    def test_unknown_filters_ignored(self):
        """Test that unknown filter keys are ignored."""
        filters = {
            "valid_key": "value",  # Will be ignored
            "source_type": "email",  # Valid, will be kept
        }
        _, _, validated = validate_search_params("test", 10, filters)
        assert validated == {"source_type": "email"}


class TestLiteralSearchParamValidation:
    """Test validate_literal_search_params function."""
    
    def test_valid_pattern(self):
        """Test valid pattern validation."""
        pattern, _, _ = validate_literal_search_params("BATES-12345")
        assert pattern == "BATES-12345"
    
    def test_empty_pattern(self):
        """Test empty pattern raises error."""
        with pytest.raises(ValidationError):
            validate_literal_search_params("")
    
    @pytest.mark.parametrize("fields,expected", [
        (None, None),
        (["body"], ["body"]),
        (["body", "metadata"], ["body", "metadata"]),
        (["title", "source_id"], ["title", "source_id"]),
    ])
    def test_valid_fields(self, fields: list, expected: list):
        """Test valid field lists."""
        _, _, validated_fields = validate_literal_search_params("test", 10, fields)
        assert validated_fields == expected
    
    def test_invalid_field_name(self):
        """Test invalid field names raise error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_literal_search_params("test", 10, ["invalid_field"])
        assert "Invalid field" in str(exc_info.value)
    
    def test_invalid_fields_type(self):
        """Test non-list fields input."""
        with pytest.raises(ValidationError) as exc_info:
            validate_literal_search_params("test", 10, "not_a_list")
        assert "list" in str(exc_info.value).lower()


class TestDateValidation:
    """Test date filter validation (RFC3339 format)."""
    
    @pytest.mark.parametrize("date", [
        "2024-01-01",
        "2024-12-31",
        "2024-01-01T00:00:00Z",
        "2024-01-01T12:34:56Z",
        "2024-01-01T12:34:56+00:00",
        "2024-01-01T12:34:56-05:00",
        "2024-01-01T12:34:56.123Z",
        "2024-01-01T12:34:56.123456Z",
    ])
    def test_valid_rfc3339_dates(self, date: str):
        """Test valid RFC3339 date formats."""
        validated = _validate_date_filter(date, "test_date")
        assert validated == date
    
    @pytest.mark.parametrize("date", [
        "01/01/2024",  # Wrong format
        "2024-13-01",  # Invalid month
        "2024-01-32",  # Invalid day
        "2024-01-01 12:00:00",  # Space instead of T
        "January 1, 2024",  # Text format
        "2024",  # Year only
        "",  # Empty
    ])
    def test_invalid_dates(self, date: str):
        """Test invalid date formats."""
        with pytest.raises(ValidationError) as exc_info:
            _validate_date_filter(date, "test_date")
        assert "RFC3339" in str(exc_info.value) or "Invalid date" in str(exc_info.value)


class TestSourceTypeValidation:
    """Test source_type filter validation."""
    
    @pytest.mark.parametrize("source_type", [
        "email",
        "email_message",
        "email_summary",
        "document",
        "document_chunk",
        "note",
    ])
    def test_valid_source_types(self, source_type: str):
        """Test valid source type values."""
        validated = _validate_source_type_filter(source_type)
        assert validated == source_type
    
    @pytest.mark.parametrize("source_type", [
        "invalid",
        "Email",  # Case sensitive
        "doc",
        "",
        123,
    ])
    def test_invalid_source_types(self, source_type: Any):
        """Test invalid source type values."""
        with pytest.raises(ValidationError):
            _validate_source_type_filter(source_type)


class TestControlCharacterRemoval:
    """Test control character removal function."""
    
    def test_removes_control_chars(self):
        """Test removal of ASCII control characters."""
        text = "Hello\x00World\x01\x02\x03"
        cleaned = _remove_control_characters(text)
        assert cleaned == "HelloWorld"
    
    def test_preserves_whitespace(self):
        """Test that tab, newline, carriage return are preserved."""
        text = "Line 1\nLine 2\tTabbed\rReturn"
        cleaned = _remove_control_characters(text)
        assert cleaned == text
    
    def test_preserves_unicode(self):
        """Test that unicode characters are preserved."""
        text = "Unicode: ñ漢字🎉émoji"
        cleaned = _remove_control_characters(text)
        assert cleaned == text


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_very_long_query(self):
        """Test query length limit."""
        long_query = "a" * 1001  # Over the 1000 char limit
        with pytest.raises(ValidationError) as exc_info:
            _validate_query(long_query)
        assert "too long" in str(exc_info.value).lower()
    
    def test_query_with_control_chars(self):
        """Test query with control characters gets cleaned."""
        query = "test\x00query\x01with\x02control"
        validated = _validate_query(query)
        assert validated == "testquerywithcontrol"
    
    def test_nested_filters(self):
        """Test deeply nested filter structures."""
        filters = {
            "tags": ["tag1", "tag2", "tag3"],
            "date_from": "2024-01-01",
        }
        _, _, validated = validate_search_params("test", 10, filters)
        assert validated["tags"] == ["tag1", "tag2", "tag3"]
    
    def test_filter_string_length_limit(self):
        """Test filter string length limits."""
        long_party = "a" * 201  # Over 200 char limit
        filters = {"party": long_party}
        with pytest.raises(ValidationError) as exc_info:
            validate_search_params("test", 10, filters)
        assert "too long" in str(exc_info.value).lower()


class TestFuzzTesting:
    """Fuzz testing with random inputs."""
    
    @pytest.mark.parametrize("_", range(100))  # Run 100 random tests
    def test_random_unicode_queries(self, _):
        """Test with random unicode strings."""
        # Generate random unicode string
        length = random.randint(1, 100)
        unicode_chars = [
            chr(random.randint(0x0020, 0xD7FF))  # Valid unicode range
            for _ in range(length)
        ]
        query = ''.join(unicode_chars)
        
        # Should either validate or raise ValidationError
        try:
            validated = _validate_query(query)
            assert isinstance(validated, str)
            assert len(validated) <= 1000
        except ValidationError:
            # This is acceptable if the input is truly invalid
            pass
    
    @pytest.mark.parametrize("_", range(50))
    def test_random_limit_values(self, _):
        """Test with random limit values."""
        # Generate various types of limit values
        limit_choices = [
            random.randint(-1000, 1000),
            random.random() * 1000,
            str(random.randint(0, 500)),
            random.choice([None, [], {}, "abc"]) if random.random() > 0.7 else 50,
        ]
        limit = random.choice(limit_choices)
        
        try:
            validated = _validate_limit(limit)
            assert 1 <= validated <= 200
        except ValidationError:
            # Expected for non-numeric values
            assert not isinstance(limit, (int, float, str))
    
    def test_sql_injection_patterns(self):
        """Test that SQL injection patterns are safely handled."""
        injection_patterns = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM sensitive --",
        ]
        
        for pattern in injection_patterns:
            # Should validate without issues (sanitization is DB layer's job)
            validated = _validate_query(pattern)
            assert isinstance(validated, str)
            # Control characters should be removed
            assert '\x00' not in validated


class TestIntegration:
    """Integration tests for full validation flow."""
    
    def test_search_params_full_validation(self):
        """Test complete search parameter validation."""
        query = "  legal contract dispute  "
        limit = 250  # Will be clamped
        filters = {
            "date_from": "2024-01-01",
            "date_to": "2024-12-31T23:59:59Z",
            "source_type": "document",
            "party": "Acme Corp",
            "tags": ["urgent", "review"],
            "unknown_key": "ignored",
        }
        
        validated_query, validated_limit, validated_filters = validate_search_params(
            query, limit, filters
        )
        
        assert validated_query == "legal contract dispute"
        assert validated_limit == 200  # Clamped
        assert validated_filters["source_type"] == "document"
        assert validated_filters["party"] == "Acme Corp"
        assert "unknown_key" not in validated_filters
    
    def test_literal_search_full_validation(self):
        """Test complete literal search parameter validation."""
        pattern = "  BATES-12345  "
        limit = -10  # Will be clamped to 1
        fields = ["body", "metadata", "title"]
        
        validated_pattern, validated_limit, validated_fields = validate_literal_search_params(
            pattern, limit, fields
        )
        
        assert validated_pattern == "BATES-12345"
        assert validated_limit == 1
        assert validated_fields == ["body", "metadata", "title"]
    
    def test_validation_performance(self):
        """Test that validation is performant."""
        import time
        
        start = time.time()
        for _ in range(1000):
            validate_search_params(
                "test query",
                50,
                {"source_type": "email", "date_from": "2024-01-01"}
            )
        elapsed = time.time() - start
        
        # Should validate 1000 calls in under 0.5 seconds
        assert elapsed < 0.5, f"Validation too slow: {elapsed:.2f}s for 1000 calls"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])