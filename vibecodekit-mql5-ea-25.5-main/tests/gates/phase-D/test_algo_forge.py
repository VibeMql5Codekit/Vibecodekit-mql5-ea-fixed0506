"""Phase D Algo Forge unit tests — 4 cases.

We exercise the API wrappers with a synthetic in-process transport so
the tests run offline.
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass

from vibecodekit_mql5 import forge_init, forge_pr


@dataclass
class _Stub:
    status: int
    body: dict
    seen: list[str]

    def __call__(self, req: urllib.request.Request) -> tuple[int, dict]:
        self.seen.append(req.get_full_url())
        return self.status, self.body


def test_init_repo_success() -> None:
    stub = _Stub(status=201, body={"id": 1, "name": "demo"}, seen=[])
    rep = forge_init.init_repo("demo", token="t", transport=stub)
    assert rep.ok
    assert rep.status == 201
    assert stub.seen[0].endswith("/repos")


def test_init_repo_failure_propagates_error() -> None:
    stub = _Stub(status=422, body={"error": "name taken"}, seen=[])
    rep = forge_init.init_repo("demo", token="t", transport=stub)
    assert not rep.ok
    assert "name taken" in rep.error


def test_pr_retries_once_on_401() -> None:
    call_count = {"n": 0}

    def tx(req: urllib.request.Request) -> tuple[int, dict]:
        call_count["n"] += 1
        return (401, {"error": "stale token"}) if call_count["n"] == 1 \
            else (201, {"number": 7})

    rep = forge_pr.open_pr(
        forge_pr.PrSpec(repo="me/x", head="feat", base="main", title="t"),
        token="t", transport=tx,
    )
    assert rep.ok
    assert call_count["n"] == 2


def test_list_repos_returns_array() -> None:
    stub = _Stub(status=200, body={"repos": ["a", "b"]}, seen=[])
    rep = forge_init.list_repos(token="t", transport=stub)
    assert rep.ok
    assert rep.body == {"repos": ["a", "b"]}
