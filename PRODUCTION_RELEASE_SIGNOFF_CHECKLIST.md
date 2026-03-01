# Production Release Sign-Off Checklist (AFIRGen)

Use this single-page checklist as a go/no-go gate for production deployment.

> Decision rule: **GO only if all P0 and P1 items are complete** and no unresolved High/Critical issues remain.

---

## P0 — Blocking (must pass before deploy)

### Security & Configuration
- [ ] Production `.env` is generated from template and all defaults replaced.
- [ ] `FIR_AUTH_KEY`, `API_KEY`, and `MYSQL_PASSWORD` are strong and rotated/stored securely.
- [ ] `CORS_ORIGINS` is explicitly set to trusted domains (no `*` in production).
- [ ] Rate-limit and session timeout values are production-calibrated.
- [ ] Security headers are present on all HTTP responses.

### Code/Architecture Risks (from latest review)
- [ ] Rate limiter no longer trusts spoofable forwarded headers unless trusted proxy policy is configured.
- [ ] FIR generation does not silently fabricate critical legal identity/location fields.
- [ ] `/authenticate` auth contract is explicitly decided and documented (dual-key vs endpoint-only auth).

### Test Coverage Gates
- [ ] Endpoint tests cover all public/operational routes:
  - [ ] `/process`
  - [ ] `/validate`
  - [ ] `/session/{session_id}/status`
  - [ ] `/regenerate/{session_id}`
  - [ ] `/authenticate`
  - [ ] `/fir/{fir_number}`
  - [ ] `/fir/{fir_number}/content`
  - [ ] `/health`
  - [ ] `/metrics`
  - [ ] `/prometheus/metrics`
  - [ ] `/reliability`
  - [ ] `/reliability/circuit-breaker/{name}/reset`
  - [ ] `/reliability/auto-recovery/{name}/trigger`
  - [ ] `/view_fir_records`
  - [ ] `/view_fir/{fir_number}`
  - [ ] `/list_firs`

### AWS/IaC Correctness
- [ ] CloudWatch validation script path mismatch is fixed and validation passes.
- [ ] Terraform syntax/plan checks pass for deployment workspace.
- [ ] Alarm topics/subscriptions are verified and test notifications are received.

---

## P1 — Required for release sign-off

### Security Verification Checklist (execution)
- [ ] Automated security tests pass (CORS/rate-limit/input/auth/headers/upload/session).
- [ ] Manual abuse tests completed (XSS, SQLi, unauthorized origin, rate-limit behavior).
- [ ] No sensitive data leaks in API error payloads/logs.

### Reliability & Operations
- [ ] Health checks pass for all services and dependencies.
- [ ] Circuit-breaker and auto-recovery paths are tested in staging.
- [ ] Graceful shutdown test completed with no data loss/regression.
- [ ] Dashboards display API/error/latency/FIR/model/database/cache/rate-limit/auth metrics.

### AWS Security Posture
- [ ] Security groups reviewed: no broad admin ingress, least privilege enforced.
- [ ] VPC endpoints/security controls validated for required services.
- [ ] Security Hub findings reviewed; no unapproved High/Critical items.

---

## P2 — Post-launch hardening (track to completion)

- [ ] Weekly uptime + incident trend review is established.
- [ ] Monthly SLA verification (99.9%) and threshold tuning performed.
- [ ] Chaos/reliability drills are scheduled and runbook updates captured.
- [ ] Quarterly security review and dependency patch cycle completed.

---

## Evidence Pack (attach to release ticket)

- [ ] CI run URLs for unit/integration/regression suites.
- [ ] Security test output artifacts.
- [ ] Terraform plan/apply output + drift check.
- [ ] CloudWatch dashboard screenshots + alarm test evidence.
- [ ] Sign-offs: Engineering, QA, SRE/DevOps, Security.

---

## Final Go/No-Go

- [ ] **GO**: All P0 + P1 complete, evidence attached, explicit approvers recorded.
- [ ] **NO-GO**: Any P0/P1 gap, unresolved High/Critical issue, or missing evidence.
