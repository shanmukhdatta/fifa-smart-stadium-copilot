# Architecture — Full Vision vs. MVP

This project was designed against an 11-layer target architecture (user interaction,
security, orchestration, planning, parallel agents, knowledge + live data, decision
fusion, recommendation generation, response delivery, monitoring, continuous learning).
That full design is a reasonable target for a production system built by a team over
weeks. This MVP implements a working vertical slice of it, chosen so that every box on
the diagram below that's marked **[MVP]** is real, running code — not a stub.

```
User Request (Fan / Staff / Volunteer)                           [MVP: FastAPI + demo frontend]
        │
        ▼
Input Validation & Security                                      [MVP: Pydantic + JWT + prompt-injection guard]
   Authentication · Validation · Prompt-injection detection
        │
        ▼
LangGraph Planning Engine                                         [MVP: keyword-based planner node]
   Intent detection · Agent selection
        │
   ┌────┼────┬────────────┐
   ▼    ▼    ▼            ▼
Navigation Crowd Accessibility Emergency                          [MVP: all 4, async, real]
        │
        ▼
Knowledge + Live Data                                              [MVP: FAISS/TF-IDF RAG + mocked live feeds]
   RAG (stadium docs) · Live data (crowd/weather/parking/transport)
        │
        ▼
Decision Fusion & Validation                                       [MVP: priority ranking + confidence scoring]
        │
        ▼
Response Generation                                                 [MVP: multilingual + voice-ready text]
        │
        ▼
Response Delivery                                                    [MVP: chat UI, voice output]
        │
        ▼
Monitoring / Continuous Learning                                      [Designed, not implemented — see below]
```

## Deferred by design (not partially built)

| Layer | Target design | MVP status | Why deferred rather than stubbed |
|---|---|---|---|
| OAuth | Full OAuth2 provider integration | JWT only, RBAC via role claim | OAuth needs a real identity provider behind it to demonstrate anything; a stub adds surface area without proof of correctness |
| Redis | Distributed cache | In-memory TTL cache, same `get/set` interface | Same caching *behavior* is demonstrated; swapping backend is a one-file change (`core/cache.py`) |
| Postgres | Persistent relational store | In-memory demo user store | No persistence requirement in an MVP demo; schema/migration work has no payoff without a real deployment target |
| Distributed tracing | OpenTelemetry / Jaeger | Structured logging with request IDs | Tracing infrastructure needs multiple real services to trace between; logging already gives per-request correlation |
| CI/CD | GitHub Actions pipeline | `pytest` run manually / in a local pre-submission check | No deployment target in a hackathon judging context makes a pipeline unverifiable |
| Continuous learning | Feedback-driven prompt/model updates | Not implemented | Requires production traffic and a feedback loop that doesn't exist yet |

Each of these is a one-file or one-service change to add later — nothing in the MVP's
structure would need to be re-architected to grow into the full design.
