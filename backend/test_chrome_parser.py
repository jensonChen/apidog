import pytest

from chrome_parser import parse_chrome_paste

SAMPLE_GET = """请求网址
http://192.168.0.238:8888/rest/base/BaseMessageService/queryList?refCols=default&cleanStatus=abc&msgOptionType=1
请求方法
GET
状态代码
200 OK
connection
keep-alive
content-type
application/json;charset=UTF-8
accept
application/json, text/plain, */*
authorization
bearer test-token
cookie
JSESSIONID=ABC123
host
192.168.0.238:8888
user-agent
Mozilla/5.0
"""


def test_parse_chrome_get_with_headers():
    request = parse_chrome_paste(SAMPLE_GET)
    assert request.method == "GET"
    assert "BaseMessageService/queryList" in request.url
    assert any(item.key.lower() == "authorization" for item in request.headers)
    assert any(item.key.lower() == "cookie" for item in request.headers)


def test_parse_chrome_get_with_extra_query():
    base = """请求网址
http://192.168.0.238:8888/rest/base/BaseMessageService/queryList
请求方法
GET
accept
*/*
authorization
bearer x"""
    request = parse_chrome_paste(
        base,
        payload_extra="refCols=default&msgOptionType=1",
    )
    assert "refCols=default" in request.url
    assert "msgOptionType=1" in request.url


def test_parse_chrome_post_json():
    request = parse_chrome_paste(
        """请求网址
http://192.168.0.238:8888/rest/task/list
请求方法
POST
accept
application/json
authorization
bearer token""",
        payload_extra='{"page":1,"rows":25}',
    )
    assert request.method == "POST"
    assert request.body_type == "json"
    assert '"page":1' in request.body
