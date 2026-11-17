# API Setup — every service, one by one (Hindi + English only)

This project is **local-first** and does **not** use n8n. Do not purchase a subscription or provide card details to start. Free service limits, availability and licenses can change. Review the provider documentation before using the tool in a public or commercial application.

## 0. Mandatory local AI — Ollama (NO API KEY)

1. Download Windows Ollama from https://ollama.com/download/windows
2. Run the installer. Open **Command Prompt**.
3. Run `ollama --version`, then `ollama pull llama3.2:3b`.
4. Run `ollama run llama3.2:3b` and ask "Hello in Hindi" to confirm it works. Exit using `/bye`.
5. Ollama normally starts its local service automatically on Windows. Test: `curl http://127.0.0.1:11434/api/tags`.
6. Keep `OLLAMA_URL=http://127.0.0.1:11434` and `OLLAMA_MODEL=llama3.2:3b` in `.env`.
7. For **photo analysis only**, download an additional model with `ollama pull qwen2.5vl:3b`, and keep `VISION_MODEL=qwen2.5vl:3b`. The visual model is more memory-intensive; on an 8 GB system use it only when necessary and stop other large programs.
8. If the app says model not found, run `ollama list` and set `OLLAMA_MODEL` to the exact name shown.

Only local requests to `127.0.0.1:11434` are made unless Gemini is deliberately enabled.

## 1. Open-Meteo weather — NO KEY, NO SIGNUP

1. Read https://open-meteo.com/en/docs and https://open-meteo.com/en/terms
2. No account or API key is required for permitted non-commercial usage.
3. Check in a browser: `https://api.open-meteo.com/v1/forecast?latitude=20&longitude=73.78&current=temperature_2m&timezone=Asia%2FKolkata`.
4. In the Gradio **Live Weather** tab, enter the actual town/city and press Fetch forecast.
5. The app first uses Open-Meteo geocoding, then the forecast endpoint. If the city is ambiguous, try a larger nearby city.
6. We cache weather responses locally to avoid excessive API requests. Provide Open-Meteo attribution when showing results.

Published free limit: **under 10,000 calls/day, 5,000/hour and 600/minute for non-commercial use** (subject to provider policy). Commercial deployments require a different arrangement.

## 2. NASA POWER climate history — NO KEY, NO SIGNUP

1. Documentation: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
2. No signup is required to access the public daily API.
3. Test in browser: `https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M&community=AG&longitude=73.78&latitude=20&start=20250101&end=20251231&format=JSON`
4. The Climate History agent requests daily `T2M` temperature and `PRECTOTCORR` precipitation.
5. Provide a city and a completed calendar year in the Climate tab. Large date spans can take time and the API can enforce rate limits.
6. Display the year and API source. Missing values are excluded from averages, and data is not a forecast.

## 3. Government mandi prices — data.gov.in (FREE REGISTRATION/KEY, DEPENDENT ON DATASET)

**Official catalog:** https://data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi

1. Go to https://data.gov.in/ and select **Register / Sign Up**.
2. Complete the free registration with your own email address, verify the account if asked, and log in.
3. Open your profile/dashboard. Find **API Key**, **Generate API Key**, or a similar current menu option (the portal UI can change). Copy your key.
4. Open the **Current daily price of various commodities from various markets (Mandi)** catalog at the URL above.
5. Choose the actual tabular resource that offers a **Data API** option. Click the Data API link.
6. Read the API usage instructions. Copy the **resource identifier** from the resource endpoint URL (`/resource/<RESOURCE_ID>`), NOT the catalog page ID. If the portal provides a ready example URL, use that exact resource identifier and response field names.
7. Paste both values into your local `.env`:

   ```ini
   DATA_GOV_API_KEY=YOUR_ACTUAL_FREE_API_KEY
   DATA_GOV_RESOURCE_ID=THE_SELECTED_RESOURCE_ID
   ```

8. Test via the API's own interactive example, or run the following after replacing the placeholders (keep key out of screenshots, logs and GitHub):

   ```text
   https://api.data.gov.in/resource/RESOURCE_ID?api-key=API_KEY&format=json&limit=2
   ```

9. Check whether the selected resource actually returns fields like `commodity`, `state`, `district`, `market`, `arrival_date`, `min_price`, `max_price`, and `modal_price`. If it uses different field names, adapt `app/tools.py` to that selected resource.
10. Start the local app, enter commodity **Onion**, state **Maharashtra**, and optionally a district, then press Fetch.

**Important:** An API key is not a guarantee that any given dataset is accessible, up to date, or populated for a particular market. The code reports API errors and empty results rather than making up prices. Price units should be checked against the selected resource. No payment is necessary for this project's intended test workflow, but the portal may restrict access.

## 4. Gemini 2.5 Flash-Lite — OPTIONAL FREE-TIER API KEY

Official page: https://ai.google.dev/gemini-api/docs/pricing

1. Visit https://aistudio.google.com/api-keys and sign in with a Google account permitted to use the service.
2. Create an API key in a project showing **free-tier eligibility**. Do **not** upgrade to a paid billing tier for this project.
3. Copy the key once and add it only to `.env`.
4. Set:

   ```ini
   USE_GEMINI=true
   GEMINI_API_KEY=PASTE_KEY_HERE
   GEMINI_MODEL=gemini-2.5-flash-lite
   ```

5. Restart the backend, then ask an agricultural question backed by your ingested PDFs.
6. If your country, account, model, or current quota does not permit free use, set `USE_GEMINI=false`. Ollama will continue as the primary local alternative.
7. To verify quota/status, check Google AI Studio project usage and the [pricing and rate-limits docs](https://ai.google.dev/gemini-api/docs/rate-limits).

Google notes that free-tier prompts may be used to improve products. **Do not transmit health/private profile content to Gemini.** The health specialist always uses the local model; crop photo uploads may fall back to Gemini only if you explicitly turn it on.

**Optional:** This project uses HTTPS requests to Gemini directly, not a separate paid SDK or another third-party API service.

## 5. OpenStreetMap — NO KEY, STRICT RATE LIMITS

Official policy: https://operations.osmfoundation.org/policies/nominatim/

1. Read the public service usage policy **before** enabling facility lookup.
2. Change the `.env` value `OSM_USER_AGENT` to a distinctive name that identifies your application; include a real contact method where possible.
3. Enter a town in the Health & Facilities tab and click **Find mapped facilities**. This one-time action sends the city name (not your exact address) to Nominatim, then sends a nearby hospital/clinic lookup to Overpass.
4. The app caches results for seven days. **Do not use for autocomplete, bulk extraction or many simultaneous users.** The public Nominatim service permits a maximum of one request per second across the application.
5. Display OpenStreetMap attribution. Data may be missing or stale, and a listed facility may not be open or able to provide emergency care.
6. For high-volume public launch, use a properly provisioned alternative or self-hosted location services, not the donated public instance.

No direct personal medical history should be transmitted in the geocoding request.

## 6. Telegram Bot API — OPTIONAL FREE BOT TOKEN

Official instructions: https://core.telegram.org/bots/tutorial

1. Install Telegram or open it in a browser.
2. Search for the verified **@BotFather** bot and open it.
3. Send `/newbot`.
4. Enter a bot display name, e.g. `Gram Sahayak Test`.
5. Enter an unused username that ends in `bot`.
6. BotFather gives a **bot token**. Copy it to:

   ```ini
   TELEGRAM_BOT_TOKEN=YOUR_BOTFATHER_TOKEN
   ```

7. Install the Telegram extras:

   ```bat
   pip install -r requirements-telegram.txt
   ```

8. Start the bot in a **third terminal** (keep backend running if you want Gradio at the same time):

   ```bat
   python -m app.telegram_bot
   ```

9. Open your bot's username in Telegram, press Start and send `/start`.
10. Set language via `/language hi` or `/language en`, and city via `/city Nashik`.
11. Test normal text, a voice note, and a plant photograph (vision model required for photos).
12. Test opt-in reminder with `/remind 2026-12-01 08:30 Review the weather` (use a future date, format is Asia/Kolkata).
13. The bot uses **long polling** on your PC. No webhook, domain name, n8n, or paid hosting required; your computer must be powered on for the bot to respond and send reminders.

Treat the token as a password. If accidentally published, revoke it through BotFather and replace it. Never use another user's Telegram token.

## 7. Speech Recognition — no API key

Install `pip install -r requirements-voice.txt`. The first transcription downloads the open-source **faster-whisper base** model to your machine. An internet connection is required the first time, then transcription works locally. Select the language manually as `en` or `hi` in Gradio. Microphone quality matters.

## 8. Speech Synthesis — no API key

- `TTS_BACKEND=gtts` (default): **gTTS** supports Hindi/English, uses an unofficial online Google Translate TTS interface, is free/no-key for small demos but has **no guaranteed public API or uptime**. Audio is saved in `data/audio/`.
- `TTS_BACKEND=mms`: **offline Meta MMS Hindi/English** model downloads on first use. Install `pip install -r requirements-mms.txt`. MMS TTS models use non-commercial licensing (check each model card). This consumes extra RAM, and the model switch should be tested on your PC.

Browser autoplay may require the user to start recording or interact with the page once.

## 9. Trusted documents — no API key

1. Download permitted official crop guidance PDFs from https://icar.gov.in/ or a state agriculture department.
2. Download current scheme guidelines from https://pmkisan.gov.in/ , https://pmfby.gov.in/ and https://www.myscheme.gov.in/ .
3. For general health material use approved guidance at https://www.who.int/; the app should not diagnose illness.
4. Put documents into `data/documents/`.
5. Edit `data/documents/sources.json`, e.g.:

   ```json
   {
     "downloaded_official_crop_guide.pdf": {
       "url": "https://ACTUAL_OFFICIAL_SOURCE_URL_OF_THE_DOCUMENT"
     }
   }
   ```

6. Run `python -m scripts.ingest` for working local keyword/FTS search.
7. For better multilingual **hybrid vector + keyword** retrieval, install `pip install -r requirements-rag.txt`, then run `python -m scripts.ingest --vectors`. The first run downloads the multilingual embedding model.
8. Test `http://127.0.0.1:8000/api/rag/status` to confirm nonzero document chunks.

**Do not populate the knowledge base with unverified generated text.** PDFs which are only scanned images require a separate OCR step; text extraction can fail.

## At-a-glance credential checklist

| Required to begin? | Credential | Where it goes |
|---|---|---|
| No | Ollama — no key | Ollama installed locally |
| No | Open-Meteo — no key | Automatic |
| No | NASA POWER — no key | Automatic |
| No | OSM — no key | Distinctive `OSM_USER_AGENT` |
| Optional | data.gov.in free API key + resource ID | `DATA_GOV_API_KEY`, `DATA_GOV_RESOURCE_ID` |
| Optional | Gemini free tier key | `GEMINI_API_KEY`, `USE_GEMINI=true` |
| Optional | Telegram bot token | `TELEGRAM_BOT_TOKEN` |

**Do not paste actual API keys into ChatGPT or publish `.env` to GitHub.**
