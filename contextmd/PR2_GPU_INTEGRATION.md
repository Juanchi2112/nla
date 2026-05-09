# PR 2: GPU Integration (sglang)

## Goal
Replace the mock generation logic with real LLM inference using the `sglang` engine already configured in the `nla/` directory.

## Implementation Details
- **Engine:** Use `sglang.Runtime` or the local `launch_sglang.sh` API.
- **Integration:** 
  - The `POST /api/generate` task should call the `sglang` generation endpoint (likely `/generate` or via the Python SDK).
  - Use the `stream=True` parameter in the sglang request.
  - Pipe the resulting generator into the FastAPI SSE stream.

## Handling Interrupts
- The loop must remain "interruptible."
- Before each token or after a specific token limit, the loop checks `SessionState.stop_requested` or `SessionState.update_pending`.

## Verification
- Verify that `nla/scripts/smoke_test.sh` passes.
- Ensure the FastAPI server can stream tokens from a 7b or 12b model (depending on available VRAM).
