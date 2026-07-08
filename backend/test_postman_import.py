import json

import pytest

from postman_import import import_postman_collection


POSTMAN_SAMPLE = {
    "info": {"name": "Demo API", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
    "item": [
        {
            "name": "Health",
            "item": [
                {
                    "name": "starter",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": "{{baseUrl}}/starter",
                    },
                }
            ],
        },
        {
            "name": "Query",
            "request": {
                "method": "POST",
                "header": [{"key": "Content-Type", "value": "application/json"}],
                "body": {
                    "mode": "raw",
                    "raw": '{"content":"hello"}',
                },
                "url": "{{baseUrl}}/pii_post_query",
            },
        },
    ],
    "variable": [{"key": "baseUrl", "value": "http://127.0.0.1:9019"}],
}


def test_import_postman_collection():
    project, variables = import_postman_collection(POSTMAN_SAMPLE)
    assert project.name == "Demo API"
    assert len(project.tree) == 2
    assert variables["baseUrl"] == "http://127.0.0.1:9019"

    folder = project.tree[0]
    assert folder.type == "folder"
    assert folder.name == "Health"
    assert folder.children[0].url == "{{baseUrl}}/starter"

    request = project.tree[1]
    assert request.type == "request"
    assert request.method == "POST"
    assert request.body_type == "json"
