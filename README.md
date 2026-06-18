# SingleAngle M365 API with OpenAI + xAI providers

This version adds maker-owned provider keys through Railway environment variables.

## Configure Railway variables

Set:

```text
OPENAI_API_KEY=your OpenAI key
XAI_API_KEY=your xAI key
OPENAI_MODEL=gpt-5
XAI_MODEL=grok-4.3
OPENAI_WEB_SEARCH_TOOL=web_search_preview
```

If OpenAI web search fails, try changing `OPENAI_WEB_SEARCH_TOOL` to the tool name available to your account/model.

## Deploy

Commit these files to GitHub. Railway will rebuild from the Dockerfile.

## Test

POST to:

```text
https://singleangle-api-production.up.railway.app/singleangle
```

with `tests/test_payload.json`.

## Copilot Studio

Keep the tool as maker-provided credentials for this phase. Re-upload `copilot/openapi.yaml` if Copilot Studio does not see the latest schema.
