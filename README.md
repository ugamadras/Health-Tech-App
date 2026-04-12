# Health Tech App

Greenfield scaffold for a mobile meal analyzer product with:

- a React Native mobile app
- an app API that enforces upload safety and orchestrates analysis
- an independent nutrition service for deterministic calculations
- a local nutrition reference database seeded from USDA/FDA source data

## Repository Layout

- `apps/mobile`: React Native client scaffold for capture, history, results, and exports
- `services/app-api`: upload validation, safety policy enforcement, orchestration, and exports
- `services/nutrition-service`: nutrient lookup, calorie/macronutrient math, and reference data access
- `data`: local USDA/FDA seed data used to initialize the nutrition database
- `scripts/import_nutrition_data.py`: SQLite ingestion pipeline with source versioning

## Safety Design

- All uploads pass through text and image moderation before nutrition analysis.
- Non-food images are rejected.
- Unsafe images or text, including sexual content, are rejected.
- All result payloads include a general wellness disclaimer and are phrased to avoid medical advice.
- Numeric outputs are produced by the nutrition service rather than free-form model text.

## Local Development

The repository now has root-level startup commands:

```bash
npm run web:start
npm run db:seed
npm run nutrition-service:start
npm run app-api:start
npm run mobile:start
```

Optional mobile targets:

```bash
npm run mobile:ios
npm run mobile:android
```

Python service dependencies can be installed with:

```bash
python3 -m pip install -r services/nutrition-service/requirements.txt
python3 -m pip install -r services/app-api/requirements.txt
```

Host and port can be overridden for local development:

```bash
APP_API_HOST=127.0.0.1 APP_API_PORT=8000 npm run app-api:start
NUTRITION_SERVICE_HOST=127.0.0.1 NUTRITION_SERVICE_PORT=8001 npm run nutrition-service:start
```

Verification:

```bash
npm run test:python
./apps/mobile/node_modules/.bin/tsc --noEmit -p apps/mobile/tsconfig.json
```

## OpenAI Responses API

The app API can optionally use the OpenAI Responses API for multimodal meal analysis.

Set:

```bash
export OPENAI_API_KEY=your_key_here
export OPENAI_MEAL_MODEL=gpt-4.1-mini
```

Then send a meal image as base64 in the `/meals` payload:

```json
{
  "filename": "meal.jpg",
  "mime_type": "image/jpeg",
  "size_bytes": 123456,
  "image_base64": "BASE64_IMAGE_BYTES",
  "text": "Lunch bowl with chicken and rice"
}
```

When `OPENAI_API_KEY` is present, the app API will:

- send the image and user text to the Responses API
- let the model classify food relevance and safety labels
- let the model call local nutrition tools to search food codes and calculate nutrition
- return the deterministic nutrition analysis with the non-medical disclaimer

## Local Web App

You can test the app in a browser without Expo:

```bash
sh start.sh web
```

Then open:

- `http://127.0.0.1:8000/app`

The web app supports:

- image upload plus optional meal description when `OPENAI_API_KEY` is configured
- local text-based fallback inference from the meal description when OpenAI image analysis is not configured
