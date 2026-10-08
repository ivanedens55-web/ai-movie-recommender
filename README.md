# 🎬 AI Movie Recommender

A small Streamlit web app that turns a plain-English description of what you feel like watching into a short list of movie recommendations, each with a reason it fits and a match score. It is powered by the Google Gemini API (free tier).

The project is intentionally simple: two Python files, three dependencies, no database, no accounts. It exists to show clean AI API integration in Python, including structured JSON output, response validation, and friendly error handling.

## Features

- Describe the movie you want in natural language (mood, genre, era, themes, style)
- Choose 3, 5, or 10 recommendations
- Optional genre filter and optional release-year range
- Each recommendation shows title, year, genre, a short description, why it matches, and a 0–100 match score
- The AI is asked for structured JSON, which the app parses and validates before display
- Duplicate titles, incomplete entries, and movies outside your year range are filtered out
- Friendly messages for every common failure (missing or invalid key, rate limits, network problems, malformed AI output) instead of Python tracebacks

## Demo

**Input**

> I want a funny action movie with a smart main character, preferably something from the last 10 years.

**Output (one card, illustrative)**

> 🎬 **Example Movie Title**
> **2019 · Action, Comedy**
> A short description of the movie.
> **Why you'll like it:** Explains which parts of your request this movie matches.
> **Match:** 92%

Actual recommendations vary from run to run.

<img width="2556" height="1034" alt="image" src="https://github.com/user-attachments/assets/b9e1be1b-b20e-41e9-84ef-1fc06b824c55" />
<img width="2560" height="1218" alt="image" src="https://github.com/user-attachments/assets/d581bb76-aabf-42d4-9b04-0499c60da9a8" />

## Technologies used

- Python 3.10+
- [Streamlit](https://streamlit.io/) for the web interface
- [Google Gemini API](https://ai.google.dev/) via the official `google-genai` SDK
- `python-dotenv` for loading the API key from a `.env` file

## Project structure

```
ai-movie-recommender/
├── app.py            # Streamlit UI: inputs, button, movie cards, error display
├── ai.py             # Prompt building, Gemini API call, JSON parsing and validation
├── requirements.txt  # Python dependencies
├── .env.example      # Template for your environment variables
├── .gitignore        # Keeps .env and other local files out of Git
└── README.md
```

## Setup

1. Clone the repository and enter the folder:

   ```bash
   git clone https://github.com/<your-username>/ai-movie-recommender.git
   cd ai-movie-recommender
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   # macOS / Linux
   source .venv/bin/activate
   # Windows
   .venv\Scripts\activate
   ```

3. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## API key configuration

1. Create a free Gemini API key at [Google AI Studio](https://aistudio.google.com/apikey).
2. Copy the example environment file:

   ```bash
   # macOS / Linux
   cp .env.example .env
   # Windows
   copy .env.example .env
   ```

3. Open `.env` and replace the placeholder:

   ```
   AI_API_KEY=your_real_key_here
   ```

The `.env` file is listed in `.gitignore`, so your key is never committed. The key is only read from the environment; it is not hard-coded anywhere.

**Optional:** the app uses `gemini-3.1-flash-lite` by default. To use another model, add `AI_MODEL=<model-name>` to `.env`. Google changes model names and free-tier availability over time, so check the [Gemini models page](https://ai.google.dev/gemini-api/docs/models) if the default stops working.

## Run locally

```bash
streamlit run app.py
```

Streamlit opens the app in your browser (usually at http://localhost:8501).

## Example prompts

- "A funny action movie with a smart main character, preferably from the last 10 years."
- "Something cozy and heartwarming for a rainy Sunday, nothing too sad."
- "A mind-bending sci-fi film with a twist ending, like the kind that makes you rewatch it."
- "A slow-burn psychological thriller set in a small town."
- "An animated movie adults will enjoy as much as kids."
- "A tense horror movie that relies on atmosphere rather than gore."

## How it works

1. `app.py` collects your description, the number of recommendations, and the optional genre and year filters.
2. `ai.py` builds a prompt from those inputs and sends it to Gemini with a system instruction (recommend only real films, explain each pick, avoid duplicates, be honest about uncertainty, never claim live database access) and a JSON schema for the reply.
3. The reply is parsed as JSON. If the model wraps it in Markdown fences or adds stray text, the parser recovers the JSON object; if it still can't, you see a friendly error.
4. Each movie is validated: required text fields must be present, the year must be a plausible integer, and the match score is clamped to 0–100. Duplicates and movies outside your year range are dropped, and the list is sorted by match score.
5. `app.py` displays each movie as a card.

## Error handling

| Situation | What you see |
|---|---|
| Empty description | A prompt to describe the movie first |
| "From year" later than "To year" | A warning to fix the range |
| Missing API key | Instructions to create `.env` with `AI_API_KEY` |
| Invalid API key | A message to check the key in `.env` |
| Rate limit (HTTP 429) | A message to wait and try again |
| Model not found | A message to set `AI_MODEL` |
| Server errors, timeouts, no internet | A message explaining the problem and to try again |
| Malformed or empty AI reply | A message that the reply couldn't be read |
| Any other unexpected error | A generic message, never a traceback |

## Limitations

Recommendations come from the model's training knowledge, not a live movie database. Release years or details can occasionally be wrong, and the app cannot tell you where a movie is streaming. Free-tier usage is rate-limited, and on the free tier Google may use requests to improve its models, so don't put personal information in your prompts.

## Future improvements

- Verify titles and years against a movie database API such as TMDB, and show posters
- Show where each movie is available to stream
- Let users regenerate a single recommendation or ask for "more like this one"
- Add unit tests for the parsing and validation functions
- Deploy to Streamlit Community Cloud

## License

MIT — see [LICENSE](LICENSE).
