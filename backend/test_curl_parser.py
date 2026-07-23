import pytest

from curl_parser import parse_curl


SAMPLE_CURL = """curl --location 'http://10.191.22.180:9019/pii_post_query' \\
--header 'Content-Type: application/json' \\
--data '{
  "chatMessageList": [
    {
      "textType": "currQuery",
      "content": "查询员工总数"
    }
  ],
  "isNewConversation": true,
  "session_id": "api-workbench-test-001"
}'"""


def test_parse_multiline_post_curl():
    parsed = parse_curl(SAMPLE_CURL)
    assert parsed.url == "http://10.191.22.180:9019/pii_post_query"
    assert parsed.method == "POST"
    assert parsed.headers["Content-Type"] == "application/json"
    assert parsed.follow_redirects is True
    assert "查询员工总数" in (parsed.body or "")
    assert "chatMessageList" in (parsed.body or "")


def test_parse_simple_get():
    parsed = parse_curl("curl http://127.0.0.1:9019/starter")
    assert parsed.method == "GET"
    assert parsed.url == "http://127.0.0.1:9019/starter"


def test_parse_data_raw_without_trailing_brace_in_url():
    parsed = parse_curl(
        'curl http://127.0.0.1:9019/pii_post_query/json -H "content-type: application/json" '
        '--data-raw "{\\"chatMessageList\\":[{\\"query\\": \\"test\\"}]}"'
    )
    assert parsed.url == "http://127.0.0.1:9019/pii_post_query/json"
    assert parsed.method == "POST"
