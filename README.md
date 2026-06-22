# singleangle-m365-starter

A Microsoft 365 Copilot-compatible rebuild of the `singleangle` idea.

This version does **not** rely on Claude Code local script execution. Instead:

- Microsoft 365 Copilot agent = orchestration and formatting
- REST API action = execution layer
- Python modules = research, angle generation, scoring, and brief assembly

## Architecture

```text
User -> M365 Copilot Agent -> REST action `/singleangle` -> Python logic -> JSON -> Copilot formats response
```

## Files

```text
app.py                                  # FastAPI app Copilot calls
singleangle_core/research.py             # source collection abstraction
singleangle_core/lenses.py               # six angle lenses
singleangle_core/scoring.py              # deterministic scoring
singleangle_core/brief.py                # final brief assembly
copilot/agent_instructions.md            # paste into Copilot agent instructions
copilot/openapi.yaml                     # import/use for REST action
.env.example                             # environment variables
```

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Test:

```bash
curl -X POST http://localhost:8000/singleangle \
  -H "Content-Type: application/json" \
  -d '{"topic":"AI outbound","audience":"B2B growth leaders"}'
```

## Copilot Studio / M365 Copilot integration

1. Deploy this API somewhere reachable over HTTPS.
2. In Copilot Studio, add a REST API tool/action using `copilot/openapi.yaml`.
3. Paste `copilot/agent_instructions.md` into the agent instructions.
4. Test with: "Find the strongest angle on AI outbound for growth leaders."

## Important

This starter does **not** include real Reddit, X, or web API integrations yet. Add them in `singleangle_core/research.py`.

The scoring is deterministic but intentionally simple. Replace the functions in `singleangle_core/scoring.py` with your preferred methods.
