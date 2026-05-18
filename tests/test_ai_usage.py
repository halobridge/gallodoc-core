"""Tests for the AI usage ledger helpers."""

from __future__ import annotations

from gallodoc.ai_usage import (
    add_ai_run,
    empty_ai_usage,
    estimate_cost,
    hash_text,
    summarize_ai_usage,
)


def test_empty_block_has_safe_defaults():
    e = empty_ai_usage()
    assert e["summary"]["total_runs"] == 0
    assert e["runs"] == []
    assert e["summary"]["currency"] == "USD"


def test_add_run_recomputes_summary():
    block = empty_ai_usage()
    block = add_ai_run(
        block,
        run_id="r1",
        operation="extraction",
        provider="openai",
        model="gpt-4o",
        input_tokens=100,
        output_tokens=200,
        latency_ms=500,
    )
    assert len(block["runs"]) == 1
    assert block["summary"]["total_runs"] == 1
    assert block["summary"]["total_input_tokens"] == 100
    assert block["summary"]["total_output_tokens"] == 200
    assert block["summary"]["total_tokens"] == 300


def test_add_run_never_carries_raw_prompts():
    block = add_ai_run(
        empty_ai_usage(),
        run_id="r2",
        operation="qa",
        provider="anthropic",
        model="claude-opus-4-7",
        input_tokens=10,
        output_tokens=5,
        prompt_hash="sha256:abc",
        response_hash="sha256:def",
    )
    run = block["runs"][0]
    assert run["prompt_hash"] == "sha256:abc"
    assert run["response_hash"] == "sha256:def"
    assert "raw_prompt" not in run
    assert "raw_response" not in run
    assert run["stored_prompt"] is False
    assert run["stored_response"] is False


def test_estimate_cost_uses_default_table():
    cost = estimate_cost("openai", "gpt-4o", input_tokens=1000, output_tokens=500)
    assert cost > 0


def test_estimate_cost_returns_zero_for_local_provider():
    assert estimate_cost("local", "any-model", input_tokens=100, output_tokens=50) == 0.0


def test_summarize_handles_multiple_runs():
    runs = [
        {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15, "estimated_cost": 0.001, "currency": "USD"},
        {"input_tokens": 20, "output_tokens": 10, "total_tokens": 30, "estimated_cost": 0.002, "currency": "USD"},
    ]
    s = summarize_ai_usage(runs)
    assert s["total_runs"] == 2
    assert s["total_input_tokens"] == 30
    assert s["total_output_tokens"] == 15
    assert s["total_tokens"] == 45
    assert s["estimated_total_cost"] == 0.003


def test_hash_text_returns_sha256_prefixed_string():
    h = hash_text("hello")
    assert h.startswith("sha256:")
    assert len(h) == len("sha256:") + 64


def test_unknown_provider_falls_back_to_custom():
    block = add_ai_run(
        empty_ai_usage(),
        run_id="r3",
        operation="weird_op",
        provider="some_new_provider",
        model="m",
    )
    assert block["runs"][0]["provider"] == "custom"
    assert block["runs"][0]["operation"] == "custom"
