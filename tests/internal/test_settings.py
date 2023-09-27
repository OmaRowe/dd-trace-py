import pytest

from ddtrace import config



@pytest.mark.parametrize(
    "test",
    [
        {
            "expected": {
                "trace_sample_rate": 1.0,
                "logs_injection": False,
                "trace_http_header_tags": {},
            }
        },
        {
            "env": {"DD_TRACE_SAMPLE_RATE": "0.9"},
            "expected": {
                "trace_sample_rate": 0.9,
            }
        },
        {
            "env": {"DD_TRACE_SAMPLE_RATE": "0.9"},
            "code": {
                "trace_sample_rate": 0.8,
            },
            "expected": {
                "trace_sample_rate": 0.8,
            }
        },
        {
            "env": {"DD_LOGS_INJECTION": "true"},
            "expected": {"logs_injection": True},
        },
        {
            "env": {"DD_LOGS_INJECTION": "true"},
            "code": {"logs_injection": False},
            "expected": {"logs_injection": False},
        },
        {
            "env": {"DD_TRACE_HEADER_TAGS": "X-Header-Tag-1,X-Header-Tag-2"},
            "expected": {"trace_http_header_tags": {"X-Header-Tag-1": "", "X-Header-Tag-2": ""}},
        }
    ],
)
def test_setting(test, monkeypatch):
    for env_name, env_value in test.get("env", {}).items():
        monkeypatch.setenv(env_name, env_value)
        config.reset()

    for code_name, code_value in test.get("code", {}).items():
        setattr(config, code_name, code_value)

    for expected_name, expected_value in test["expected"].items():
        assert getattr(config, expected_name) == expected_value
