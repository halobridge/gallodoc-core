---
title: "Measuring Trust in AI Decisions"
version: "1.5"
status: release-candidate
audience: "enterprise leaders; AI governance; compliance; security"
last_updated: "2026-05-01"
keywords: "trust score, decision gates, GalloDoc, AI governance"
---

# Measuring Trust in AI Decisions

## 1. Executive Summary

Enterprises deploying AI over documents need more than accuracy benchmarks. They need **governed decisions**: explicit scores, gates, policy outcomes, and receipts that explain why an action was allowed, warned, blocked, or escalated.

**GalloDoc 1.5 turns trust from a feeling into a governed decision object.**

The optional `trust_decision` envelope block standardizes trust snapshots, decision gates, policy outcomes, recommendations, and receipts — without shipping proprietary weighting formulas or sensitive payloads in open-core examples.

## 2. The Trust Gap in AI Systems

Logs show activity; they rarely prove suitability for irreversible actions. Scores without structure become slogans. Teams need machine-readable artifacts that align security, consent, execution governance, observability, and human review.

## 3. Why Logs and Scores Alone Are Not Enough

Operational telemetry lacks semantic linkage to policy. Single scalar scores hide which dimension failed. GalloDoc 1.5 preserves **components** (evidence, lifecycle, security, execution, consent/custody, residency/training/model risk, observability, human review) so reviewers see *why*, not only *how much*.

## 4. The GalloDoc 1.5 Trust Decision Model

`trust_decision` is additive under the frozen `gallodoc-core/v1` envelope. It references prior layers (1.1 execution governance, 1.2 compliance, 1.3 model risk, 1.4 observability) and projects **decision-ready** artifacts.

## 5. Trust Scores

Each **GalloTrustScore** records `score`, `grade`, `status`, timestamps, opaque `scoring_profile`, and **eight components** with explanations. Numeric weights remain enterprise-private; the open standard defines shape and safety — not vendor tuning.

## 6. Decision Gates

**GalloDecisionGate** rows evaluate actions (`export`, `send_external`, `call_external_model`, etc.) against thresholds and conditions, emitting `allow`, `warn`, `block`, or `require_review` with reason codes.

## 7. Policy Outcomes

**GalloPolicyOutcome** merges rule matches into a single outcome with warnings, blockers, and required actions — suitable for audit summaries.

## 8. Action Recommendations

**GalloActionRecommendation** captures prioritized follow-ups (`request_him_c_review`, `attach_external_evidence`, `rerun_model_verification`, …) with roles and due hints.

## 9. Decision Receipts

**GalloDecisionReceipt** binds an action to score, gate, and policy outcome IDs, plus opaque refs (evidence, execution receipts, attestations, exports, portal artifacts). Receipts answer: **what decision was taken, under which trust posture, with which artifacts.**

## 10. Enterprise Value

- Faster audit response — structured explanations instead of ad-hoc narratives.
- Safer automation — gates align high-risk actions with trust posture.
- Clear escalation — receipts preserve rationale without leaking prompts or PHI.

## 11. Conclusion

GalloDoc 1.5 completes the arc from traceable documents (1.0) through governed execution, compliance, model risk, and observability — to **trust-aware decisions**. Pair envelopes with enterprise policy engines and private scoring profiles to operationalize at scale.
