# Frontend + Backend Code Review (Bug & Alignment Audit)

Date: 2026-02-21
Scope: `AFIRGEN FINAL/frontend` and `AFIRGEN FINAL/main backend`

## Executive Summary

Critical integration and runtime defects are present:

1. **Backend fails to import due to indentation error** around middleware declarations.
2. **FIR generation path has a function-signature mismatch** (`get_fir_data` called with 2 args, defined with 1).
3. **Frontend/backend contract mismatch on regenerate flow** (frontend sends JSON body, backend expects query params).
4. **Frontend completion polling depends on fields not returned by backend status endpoint**.
5. **Frontend fetches FIR status endpoint but expects full FIR content payload**.
6. **Middleware shutdown path calls non-existent `HTTPException.to_response()`**.

These issues together can block end-to-end FIR completion in production.

---

## Findings

### 1) Backend startup/import blocker (Critical)
- `RequestTrackingMiddleware` is declared without an indented body, which causes an `IndentationError` and prevents server startup/import.  
- The middleware registration follows immediately after an empty class definition.

Evidence:
- `class RequestTrackingMiddleware(BaseHTTPMiddleware):` with no body.【F:AFIRGEN FINAL/main backend/agentv5.py†L1693-L1695】

Impact:
- FastAPI app cannot start; all backend functionality is unavailable.

---

### 2) FIR generation runtime crash due to function signature mismatch (Critical)
- `get_fir_data` is defined with one parameter (`session_state`).【F:AFIRGEN FINAL/main backend/agentv5.py†L215-L216】
- During FIR narrative approval, code calls `get_fir_data(state_dict, fir_number)` with two arguments.【F:AFIRGEN FINAL/main backend/agentv5.py†L1869-L1873】

Impact:
- Raises `TypeError` at runtime during final FIR construction, preventing FIR creation and persistence.

---

### 3) Regenerate endpoint request-shape mismatch (High)
- Backend endpoint signature defines `step` and `user_input` as function params (query/form style by default), not a JSON body model.【F:AFIRGEN FINAL/main backend/agentv5.py†L1950-L1952】
- Frontend sends `step` and `user_input` in JSON body to `/regenerate/{sessionId}`.【F:AFIRGEN FINAL/frontend/js/api.js†L451-L460】

Impact:
- Likely 422 validation errors or ignored payload, breaking regeneration UX.

Recommendation:
- Backend should accept `RegenerateRequest` body (already defined in validation module) or frontend should move params to query string.

---

### 4) Session completion polling mismatch (High)
- Frontend polling expects `status.validation_history[-1].content.fir_number` on `/session/{id}/status`.【F:AFIRGEN FINAL/frontend/js/api.js†L551-L553】
- Backend status endpoint returns only basic fields (`session_id`, `status`, `current_step`, timestamps) and **does not include** `validation_history` or `fir_number`.【F:AFIRGEN FINAL/main backend/agentv5.py†L1940-L1948】

Impact:
- Polling cannot resolve FIR number; completion callback may never render final FIR.

---

### 5) FIR retrieval endpoint mismatch (Medium)
- Frontend `getFIR()` calls `/fir/{firNumber}` and completion UI expects `firData.content`.【F:AFIRGEN FINAL/frontend/js/api.js†L515-L531】【F:AFIRGEN FINAL/frontend/js/app.js†L136-L140】
- Backend `/fir/{fir_number}` intentionally returns metadata only (no full content).【F:AFIRGEN FINAL/main backend/agentv5.py†L2054-L2060】
- Backend has separate `/fir/{fir_number}/content` endpoint for full FIR payload.【F:AFIRGEN FINAL/main backend/agentv5.py†L2068-L2086】

Impact:
- UI may render blank/undefined FIR content post-completion.

---

### 6) Invalid response construction in shutdown path (Medium)
- In request tracking middleware, code attempts `HTTPException(...).to_response()`.【F:AFIRGEN FINAL/main backend/agentv5.py†L1616-L1619】
- `HTTPException` has no `to_response()` method in FastAPI/Starlette.

Impact:
- During shutdown edge cases, this can raise a secondary exception and mask original failure.

Recommendation:
- Return `JSONResponse(status_code=503, content={...})` or raise `HTTPException` and let FastAPI handler serialize it.

---

## Overall Alignment Assessment

- **Backend runtime stability:** Not aligned (import/startup broken).
- **Frontend ↔ backend API contracts:** Partially aligned but with high-impact mismatches in completion and regenerate flows.
- **Production readiness:** Blocked until critical and high findings are fixed.

## Suggested Fix Order

1. Fix indentation/import blocker in backend middleware region.
2. Fix `get_fir_data` call signature mismatch.
3. Normalize regenerate contract (JSON body model recommended).
4. Align completion data path:
   - either include `fir_number` in session status response, or
   - stop polling after final `/validate` response and use returned `content` directly.
5. Update frontend to call `/fir/{fir_number}/content` when full FIR text is needed.
6. Replace invalid `to_response()` shutdown handling.


## Additional Issues Identified (Second Pass)

### 7) Text-only `/process` sessions are never marked `AWAITING_VALIDATION` (High)
- `create_session()` always initializes status as `PROCESSING`.
- In text-only flow, code sets `state.awaiting_validation = True` but does **not** call `set_session_status(..., AWAITING_VALIDATION)` before returning.
- `/validate` explicitly rejects sessions whose status is not `AWAITING_VALIDATION`.

Evidence:
- Session creation defaults to `SessionStatus.PROCESSING`.【F:AFIRGEN FINAL/main backend/agentv5.py†L366-L373】
- Text path sets validation step/flags but no status transition call nearby.【F:AFIRGEN FINAL/main backend/agentv5.py†L1755-L1764】
- `/validate` gate checks strict status equality against `AWAITING_VALIDATION`.【F:AFIRGEN FINAL/main backend/agentv5.py†L1798-L1802】

Impact:
- Text-only submissions can get stuck and fail validation with “Session not awaiting validation”.

---

### 8) Frontend allows file combinations backend rejects (High)
- UI enables generation when **either or both** `letterFile` and `audioFile` are present.
- Backend `/process` rejects requests containing more than one input type.

Evidence:
- Frontend computes readiness as `letterFile || audioFile`, with no exclusivity enforcement.【F:AFIRGEN FINAL/frontend/js/app.js†L19-L27】
- Backend enforces exactly one input (`input_count > 1` => 400).【F:AFIRGEN FINAL/main backend/agentv5.py†L1716-L1719】

Impact:
- Users can select both uploads and hit a guaranteed backend 400 error.

---

### 9) Frontend accepted file types exceed what backend supports (High)
- Letter uploader accepts `.pdf/.txt/.doc/.docx`, but backend only supports image uploads (`jpeg/png`) or text field.
- Audio uploader accepts `.m4a/.ogg`, but backend MIME allowlist does not include these audio formats.

Evidence:
- Frontend letter allowlist includes document formats.【F:AFIRGEN FINAL/frontend/js/app.js†L399-L403】
- Frontend audio allowlist includes `.m4a` and `.ogg`.【F:AFIRGEN FINAL/frontend/js/app.js†L440-L444】
- Backend file validation allowlists only JPEG/PNG for image and WAV/MPEG/MP3 for audio.【F:AFIRGEN FINAL/main backend/input_validation.py†L27-L31】

Impact:
- Frontend validates and accepts files that backend rejects (415) or cannot process correctly.

---

### 10) Non-image letter files are read via `File.text()` (Medium)
- For any non-image “letter file”, frontend calls `await letterFile.text()` and sends that as form `text`.

Evidence:
- `processFiles()` uses `letterFile.text()` whenever MIME is not image/*.【F:AFIRGEN FINAL/frontend/js/api.js†L311-L316】

Impact:
- Binary formats like PDF/DOC/DOCX are decoded as text incorrectly, causing corrupted payloads, likely validation failures, and poor UX.

---

### 11) Authentication middleware appears duplicated/nested incorrectly (Medium)
- `APIAuthMiddleware` is defined once and added.
- A second `APIAuthMiddleware` class appears nested later inside another class block region, followed by indentation corruption at `RequestTrackingMiddleware`.

Evidence:
- First middleware declaration and registration region begins earlier in the middleware section; later duplicated nested declaration appears before the indentation break region.【F:AFIRGEN FINAL/main backend/agentv5.py†L1523-L1695】

Impact:
- Increases risk of dead code, confusing behavior, and maintenance errors; contributed to structural corruption in this section.

---

## Updated Priority After Second Pass

1. Fix backend structural/indentation corruption and remove duplicated middleware declarations.
2. Fix text-only status transition to `AWAITING_VALIDATION` before returning from `/process`.
3. Align frontend upload constraints with backend allowlists and single-input rule.
4. Fix regenerate/session/FIR endpoint contract mismatches from initial report.
5. Replace `File.text()` path for binary docs with explicit unsupported-type handling or proper server-side OCR/doc parsing pipeline.
