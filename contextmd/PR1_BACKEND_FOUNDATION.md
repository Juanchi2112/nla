# PR 1: Backend Foundation & Session Management

## Goal
Establish the core FastAPI server and the in-memory session routing logic required to handle asynchronous steering commands while streaming tokens.

## Proposed Infrastructure
- **Framework:** FastAPI
- **Server:** Uvicorn
- **State Management:** A global `Dict[str, SessionState]` to track active generations.

## API Specification

### 1. `POST /api/generate`
- **Body:** `{ "session_id": UUID, "prompt": str, "model": str }`
- **Action:** Initializes the `SessionState` for the given ID. Starts an async background task to simulate token generation.

### 2. `GET /api/stream/{session_id}`
- **Response:** `text/event-stream`
- **Action:** Yields SSE events from the session's buffer.
- **Events:**
  - `token`: Individual text chunks.
  - `nla_trace`: Mock judge scores and internal monologue.
  - `done`: Finalization signal.

### 3. `POST /api/steer`
- **Body:** `{ "session_id": UUID, "rubric": str, "intensity": float }`
- **Action:** Updates the `SessionState.active_rubric` flag. The simulation loop should detect this and change its mock output (e.g., prefixing tokens with "[STEERED]").

## Verification
- Use `curl --no-buffer http://localhost:8000/api/stream/{uuid}`.
- Trigger `/api/steer` in a separate terminal and observe the stream's reaction.
