# Nexus Dynamics Platform Architecture Guidelines

## Context & Scope
Nexus Dynamics operates a distributed candidate evaluation and adaptive assessment platform. All microservices must comply with platform reliability, security, and low-latency standards.

## Platform Standards & Service Level Objectives
1. **API Latency:** P99 response time for assessment queries must remain under 200 milliseconds.
2. **Deterministic Evaluation:** All grading and rubric evaluation logic must produce reproducible scores for identical input parameters. Probabilistic models must be anchored by grounded retrieval citations.
3. **Multi-Tenant Isolation:** Assessment sessions and candidate data must be partitioned by tenant identifier. Data from one candidate evaluation session must never leak into shared model context or unauthenticated endpoints.

## Microservices Communication
- **Synchronous Services:** Inter-service REST APIs must define rigid OpenAPI / Pydantic schemas. Timeouts must be bounded (default 3 seconds), with exponential backoff on retryable transient network errors.
- **Asynchronous Workflows:** Heavy scoring pipelines, document parsing, and vector indexing must run asynchronously using dedicated worker processes.

## Evidence Verification
When scoring candidate responses, the system must reference verified Knowledge Base chunks using stable chunk IDs. Speculative evaluations or claims lacking retrieved evidence must be classified as `insufficient_evidence` rather than asserted as factual ground truth.

