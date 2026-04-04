"""Tests for aegis.observe.tokens — multi-format token extraction."""

from __future__ import annotations

from aegis.observe.tokens import TokenUsage, extract_tokens


class TestTokenUsage:
    def test_defaults(self):
        u = TokenUsage()
        assert u.input_tokens == 0
        assert u.output_tokens == 0
        assert u.total_tokens == 0

    def test_auto_total(self):
        u = TokenUsage(input_tokens=100, output_tokens=50)
        assert u.total_tokens == 150

    def test_explicit_total(self):
        u = TokenUsage(input_tokens=100, output_tokens=50, total_tokens=200)
        assert u.total_tokens == 200

    def test_frozen(self):
        u = TokenUsage(input_tokens=1)
        try:
            u.input_tokens = 2  # type: ignore[misc]
            assert False, "should be frozen"
        except AttributeError:
            pass


class TestExtractOpenAI:
    def test_standard(self):
        resp = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            }
        }
        u = extract_tokens(resp)
        assert u.input_tokens == 100
        assert u.output_tokens == 50
        assert u.total_tokens == 150

    def test_missing_completion(self):
        resp = {"usage": {"prompt_tokens": 80}}
        u = extract_tokens(resp)
        assert u.input_tokens == 80
        assert u.output_tokens == 0


class TestExtractAnthropic:
    def test_standard(self):
        resp = {"usage": {"input_tokens": 200, "output_tokens": 100}}
        u = extract_tokens(resp)
        assert u.input_tokens == 200
        assert u.output_tokens == 100
        assert u.total_tokens == 300

    def test_no_usage_key(self):
        u = extract_tokens({"content": "hello"})
        assert u.total_tokens == 0


class TestExtractGeneric:
    def test_flat_dict(self):
        resp = {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
        u = extract_tokens(resp)
        assert u.input_tokens == 10
        assert u.total_tokens == 30

    def test_empty(self):
        u = extract_tokens({})
        assert u.total_tokens == 0


class TestExtractObject:
    def test_object_with_dict(self):
        class FakeResponse:
            def __init__(self):
                self.usage = {"input_tokens": 50, "output_tokens": 25}

        u = extract_tokens(FakeResponse())
        assert u.input_tokens == 50
        assert u.output_tokens == 25

    def test_object_with_model_dump(self):
        class FakeUsage:
            def model_dump(self):
                return {"input_tokens": 60, "output_tokens": 30}

        class FakeResponse:
            def model_dump(self):
                return {"usage": {"input_tokens": 60, "output_tokens": 30}}

        u = extract_tokens(FakeResponse())
        assert u.input_tokens == 60

    def test_non_dict_non_object(self):
        u = extract_tokens(42)
        assert u.total_tokens == 0

    def test_none_response(self):
        u = extract_tokens(None)
        assert u.total_tokens == 0
