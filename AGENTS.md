# AGENTS.md

## Purpose

This repository contains a local meal analyzer application centered around a FastAPI backend and a simple browser UI.

The current primary experience is the web app served from the app API at:

- `http://127.0.0.1:8000/app`

The web flow is image-first and uses OpenAI APIs plus USDA FoodData Central to identify meal items and show nutrition context.

## Repository Layout

- `services/app-api`: main backend, web UI assets, OpenAI orchestration, USDA integration
- `services/nutrition-service`: legacy deterministic nutrition service scaffold
- `apps/mobile`: React Native scaffold, not the primary local testing surface
- `data`: local seed/reference data
- `scripts`: local startup and utility scripts

## Primary Runtime Architecture

The active analysis pipeline in `services/app-api` is:

1. OpenAI Moderations API
2. Responses API observer model for `food | non_food | uncertain`
3. Responses API inference model for meal item extraction
4. USDA FoodData Central tool calls executed by the app backend
5. Responses API output reviewer

Follow-up meal questions use:

1. Responses API answer generation
2. Responses API output safety review
3. Appended disclaimer

## Current Model Defaults

Defined in `services/app-api/src/app_api/openai_responses.py`:

- moderation: `omni-moderation-latest`
- observer: `gpt-5.4-nano`
- meal inference: `gpt-5.4-mini`
- output reviewer: `gpt-5.4-nano`
- follow-up Q&A: `gpt-5.4-mini`
- follow-up answer reviewer: `gpt-5.4-nano`

Environment variables:

- `OPENAI_API_KEY`
- `OPENAI_MEAL_MODEL`
- `OPENAI_OBSERVER_MODEL`
- `OPENAI_OUTPUT_REVIEW_MODEL`
- `USDA_API_KEY`

## Tool-Calling Ownership

USDA tool calls are executed by the app backend, not by OpenAI directly.

The flow is:

1. The backend sends a Responses API request.
2. The model emits tool calls such as `search_usda_foods` or `get_usda_food_details`.
3. The backend executes those tools in Python.
4. The backend sends the tool outputs back to the Responses API.

Relevant files:

- `services/app-api/src/app_api/openai_responses.py`
- `services/app-api/src/app_api/usda_client.py`

## Local Startup Commands

From the repo root:

- `sh start.sh web`
- `sh start.sh web-bg`
- `sh stop.sh web`
- `sh stop.sh all`
- `npm run test:python`

Useful endpoints:

- `/`
- `/health`
- `/docs`
- `/app`

## UI Notes

The browser app lives in:

- `services/app-api/src/app_api/static/index.html`
- `services/app-api/src/app_api/static/app.js`
- `services/app-api/src/app_api/static/app.css`

The UI currently shows:

- moderation stage
- observer stage
- inference stage
- output reviewer stage
- inferred meal items
- USDA-backed nutrition summary
- follow-up nutrition Q&A
- per-stage timing information

## Safety and Product Constraints

- Unsafe image or text content must be rejected before inference.
- Non-food uploads should not continue to detailed meal inference.
- Output must avoid medical advice.
- Every analysis result and follow-up answer must include a disclaimer.
- The disclaimer should state that values are estimates and actual quantities may vary.

## Important Implementation Files

- `services/app-api/src/app_api/api.py`: routes and web app serving
- `services/app-api/src/app_api/analysis.py`: orchestration and nutrition summary assembly
- `services/app-api/src/app_api/openai_responses.py`: OpenAI calls, tool loop, output review, Q&A
- `services/app-api/src/app_api/policy.py`: validation rules
- `services/app-api/src/app_api/models.py`: shared models and disclaimer text
- `services/app-api/src/app_api/storage.py`: in-memory meal storage
- `services/app-api/src/app_api/usda_client.py`: USDA FoodData Central client

## Testing Guidance

Primary verification command:

- `npm run test:python`

If changing the web UI, also manually verify:

1. image upload works at `/app`
2. stage timings render correctly
3. long text wraps inside cards
4. follow-up question output keeps the disclaimer highlighted

## Editing Guidance

- Prefer updating the web app flow over the mobile scaffold unless the task explicitly targets mobile.
- Keep the README and this file aligned when the architecture changes materially.
- Do not reintroduce filename-based meal inference.
- Preserve the separation between moderation, observer, inference, and output review stages.
