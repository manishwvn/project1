# Learning Log — Agentic AI Step by Step

Goal: learn LangGraph, Langfuse, tool calls, memory, RAG — step by step —
while building a naive iOS chat app as the front end. Backend LLM calls use
Groq (free tier) and later OpenRouter, not Anthropic API (no budget for that).
Claude Code is the dev tool writing all code.

## Step 1 — Bare backend, no agent logic yet

**What:** `backend/` — a uv-managed Python 3.12 project with FastAPI +
Groq SDK. One endpoint: `POST /chat` — takes `{"message": "..."}`, sends it
straight to Groq's `qwen/qwen3-32b` model, returns `{"reply": "..."}`.
Qwen3 is a reasoning model — Groq's `reasoning_format="hidden"` param
suppresses the `<think>...</think>` block so only the final answer comes
back.

**Why this first:** no agent framework yet on purpose. Before LangGraph adds
orchestration, want plain request -> LLM -> response working, so later when
LangGraph is introduced it's clear what it's adding (graph state, multi-step
reasoning, tool routing) rather than mixing that with "does the API call even
work."

**Why uv:** fast, single tool for venv + dependency + Python version pinning.
Avoids juggling pip/venv/pyenv separately.

**Why FastAPI:** minimal boilerplate, async-friendly, will matter once
tool-calling / streaming responses come in later steps. Also the natural
counterpart to a SwiftUI client talking HTTP.

**Files:**
- `backend/main.py` — the FastAPI app + `/chat` route
- `backend/pyproject.toml` — deps: fastapi, uvicorn, groq, python-dotenv
- `.env` (repo root, gitignored) — holds `GROQ_API_KEY`

**How to run:**
```
cd backend
uv run uvicorn main:app --port 8000 --reload
```
Test:
```
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"say hi in 3 words"}'
```

**Verified:** server boots, `/chat` returns a real Groq completion.

## Step 2 — Bare SwiftUI iOS chat screen

**What:** `ios/ChatApp/` — Xcode project (SwiftUI, iOS App template), lives
inside `project1` repo so backend and frontend version together. Single
screen: text field, Send button, scrollable reply area. On Send, POSTs
`{"message": "..."}` to `http://localhost:8000/chat`, decodes
`{"reply": "..."}`, shows it.

**Why:** simplest possible client to prove backend is reachable from a real
app shell before layering any agent logic in. No chat history, no styling —
just request/response wired up.

**Files:**
- `ios/ChatApp/ChatApp/ContentView.swift` — the whole UI + networking
  (`ChatRequest`/`ChatResponse` Codable structs, `URLSession` POST call)
- `ios/ChatApp/ChatApp.xcodeproj` — created via Xcode's New Project wizard
  (can't be scripted cleanly from CLI)

**How to run:** open `ChatApp.xcodeproj` in Xcode, run on iOS Simulator.
Backend must be running (`uv run uvicorn main:app --port 8000 --reload` in
`backend/`) — simulator can reach `localhost:8000` directly.

**Verified:** ran in Simulator with backend live — multi-turn conversation
works end-to-end.

**Polish pass (same step):** chat bubbles (blue = user, gray = assistant),
auto-scroll to newest message, loading spinner while waiting on a reply,
text field clears after send, Return key sends (`.onSubmit`), tap outside
dismisses keyboard. Added basic markdown rendering — replies are split on
` ``` ` fences; non-code segments go through
`AttributedString(markdown:)` (bold etc.), code segments get monospaced
font + dark background, mimicking how Messages/ChatGPT render model output.

**Simulator quirk (fixed):** typing into the Simulator via automated
keystrokes kept triggering macOS's accent-picker popup and freezing input.
Cause: Simulator's I/O → Keyboard → "Connect Hardware Keyboard" was on,
which routes physical key events straight through and collides with
synthetic ones. Turned it off — Simulator falls back to its on-screen
keyboard, which takes normal taps reliably.

## Step 3 — Running on a physical iPhone (not just Simulator)

**What:** app now installs and runs on a real device over USB, talking to
the backend over the LAN instead of `localhost`.

**Changes needed:**
- `ContentView.swift` — backend URL changed from `http://localhost:8000`
  to `http://<mac-lan-ip>:8000` (phone isn't the same host as the Mac).
- `backend/main.py` run command — `uvicorn` bound to `--host 0.0.0.0`
  instead of the default `127.0.0.1`, so it accepts LAN connections, not
  just local ones.
- `Info.plist` — added `NSAppTransportSecurity` → `NSAllowsLocalNetworking`
  (iOS blocks plain HTTP by default; this exempts local-network traffic)
  and `NSLocalNetworkUsageDescription` (required prompt text for local
  network access on-device).
- Xcode signing — free Apple ID / Personal Team, no paid developer account
  needed for local device testing (app just needs re-trusting every ~7 days).
- Backend kept alive across Mac sleep/lock with
  `caffeinate -i uv run uvicorn ...` — locking the screen alone never
  kills a running process, only sleep does, and `caffeinate -i` prevents that.

**Bugs hit and fixed, in order:**
1. **Duplicate Info.plist build error** ("Multiple commands produce...") —
   this project uses Xcode's newer file-system-synchronized groups, which
   auto-includes every file in the folder as a build resource. Adding a
   custom `Info.plist` file made Xcode both copy it as a resource *and*
   process it as the app's Info.plist. Fixed with a
   `PBXFileSystemSynchronizedBuildFileExceptionSet` excluding `Info.plist`
   from resource copying.
2. **Disk full** — `dyld_shared_cache_extract_dylibs failed`. First-time
   device connection makes Xcode decompress the phone's whole system
   library cache locally (needs ~5-8GB free temporarily) so it can
   symbolicate crashes/breakpoints. Fixed by moving
   `~/Library/Developer/Xcode/iOS DeviceSupport` to an external SSD and
   symlinking it back — one-time extraction, cached permanently after,
   only re-triggers on iOS version upgrades.
3. **Missing `CFBundleIdentifier`** — turning off `GENERATE_INFOPLIST_FILE`
   (to fix bug #1) also turned off Xcode's automatic injection of required
   Info.plist keys (`CFBundleIdentifier`, `CFBundleExecutable`, etc.).
   Install failed with a generic, unhelpful Xcode error — the real reason
   only showed up via `xcrun devicectl device install app` on the CLI.
   Fixed by adding those keys back manually, referencing the build
   settings (`$(PRODUCT_BUNDLE_IDENTIFIER)` etc.) the same way Xcode's
   auto-generated plist does.
4. **Untrusted developer certificate** — free Apple ID app installs need a
   manual one-time trust: Settings → General → VPN & Device Management →
   select the cert → Trust.

**Debugging note:** Xcode's toolbar status text ("Finished running...")
was frequently stale/wrong throughout this — the Report Navigator
(Cmd+9-equivalent icon) showing per-run Build/Launch logs, and
`xcrun devicectl device info apps` / `device install app` from the
terminal, were the only reliable ground truth.

**Verified:** app installed and running on physical iPhone, reachable
over WiFi to the Mac's backend.

## Next steps (not started)
- Tool calls, memory, RAG, LangGraph orchestration, Langfuse tracing
  — one at a time, each demoed through the iOS app before moving on
- iOS work is secondary from here; agentic backend is the focus
