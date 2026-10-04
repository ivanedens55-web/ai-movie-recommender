"""AI logic for the movie recommender.

This module builds the prompt, calls the Google Gemini API, and turns the
model's JSON reply into a clean, validated list of movie recommendations.
"""

import json
import os

import httpx  # Installed with google-genai; used here to catch network errors.
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

# Gemini 3.1 Flash-Lite is on the Gemini API free tier. Set AI_MODEL in your
# .env file to use a different model without touching the code.
DEFAULT_MODEL = "gemini-3.1-flash-lite"
REQUEST_TIMEOUT_MS = 60_000

SYSTEM_INSTRUCTION = """You are a knowledgeable, honest movie recommendation assistant.

Rules:
- Recommend only real, released feature films that you are confident exist.
  Never invent titles. If unsure a film is real, leave it out.
- Prefer films you know well. If you are unsure about a detail (such as the
  exact year), say so briefly in "why_recommended" and lower the match score.
- Consider the genre, mood, era, themes, tone, and style the user describes.
- Never recommend the same movie twice. Keep the list varied: mix directors,
  decades (where the request allows), and well-known with lesser-known picks.
- You do not have access to live movie databases, ratings, or streaming
  availability. Never claim to.
- "match_score" is an integer from 0 to 100 showing how well the movie fits
  this specific request, not how good the movie is.
- Reply with JSON only, in exactly the requested structure."""

# JSON schema the model is asked to follow. We still validate the reply
# ourselves, because the model can occasionally break the rules.
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "year": {"type": "integer"},
                    "genre": {"type": "string"},
                    "description": {"type": "string"},
                    "why_recommended": {"type": "string"},
                    "match_score": {"type": "integer"},
                },
                "required": [
                    "title",
                    "year",
                    "genre",
                    "description",
                    "why_recommended",
                    "match_score",
                ],
            },
        }
    },
    "required": ["recommendations"],
}

TEXT_FIELDS = ["title", "genre", "description", "why_recommended"]


class RecommendationError(Exception):
    """An error with a message that is safe to show to the user."""


def get_api_key():
    """Read the API key from the environment, or raise a friendly error."""
    api_key = os.getenv("AI_API_KEY", "").strip()
    if not api_key or api_key == "your_api_key_here":
        raise RecommendationError(
            "No API key found. Copy .env.example to .env, add your Gemini API "
            "key as AI_API_KEY, then restart the app."
        )
    return api_key


def build_prompt(user_request, count, genre, min_year, max_year):
    """Combine the user's request and filters into one prompt for the model."""
    lines = [
        f'The user is looking for a movie. Their request: "{user_request.strip()}"',
        "",
        f"Recommend exactly {count} different movies.",
    ]
    if genre and genre != "Any":
        lines.append(f"Every movie must fit the {genre} genre.")
    if min_year and max_year:
        lines.append(f"Every movie must be released between {min_year} and {max_year}, inclusive.")
    elif min_year:
        lines.append(f"Every movie must be released in {min_year} or later.")
    elif max_year:
        lines.append(f"Every movie must be released in {max_year} or earlier.")
    lines.append("Order them from best match to weakest match.")
    return "\n".join(lines)


def call_ai(prompt, api_key):
    """Send the prompt to Gemini and return the raw text reply.

    Every API or network problem is converted into a RecommendationError
    with a message written for the user, not a traceback.
    """
    model = os.getenv("AI_MODEL", "").strip() or DEFAULT_MODEL
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
    )
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.8,  # a little creativity keeps the picks varied
        response_mime_type="application/json",
        response_json_schema=RESPONSE_SCHEMA,
        # No tools are used, so turn off automatic function calling.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    try:
        response = client.models.generate_content(
            model=model, contents=prompt, config=config
        )
    except errors.ClientError as error:
        raise RecommendationError(_client_error_message(error, model)) from error
    except errors.ServerError as error:
        raise RecommendationError(
            "The AI service is having trouble right now. Wait a minute and try again."
        ) from error
    except errors.APIError as error:
        raise RecommendationError(
            f"The AI service returned an unexpected error (code {error.code}). Try again."
        ) from error
    except httpx.TimeoutException as error:
        raise RecommendationError(
            "The AI service took too long to answer. Try again in a moment."
        ) from error
    except httpx.TransportError as error:
        raise RecommendationError(
            "Couldn't reach the AI service. Check your internet connection and try again."
        ) from error

    if not response.text:
        raise RecommendationError(
            "The AI returned an empty reply, which can happen if a request is "
            "blocked by its safety filters. Try rewording your request."
        )
    return response.text


def _client_error_message(error, model):
    """Pick a friendly message for a 4xx error from the API."""
    details = f"{error.status or ''} {error.message or ''}".lower()

    if error.code == 429:
        return (
            "You've hit the API rate limit (common on the free tier). "
            "Wait a minute and try again."
        )
    if error.code in (401, 403) or "api key" in details or "api_key" in details:
        return (
            "Your API key was rejected. Check that AI_API_KEY in your .env file "
            "is a valid Gemini API key, then restart the app."
        )
    if error.code == 404:
        return (
            f'The model "{model}" was not found. Set AI_MODEL in your .env file '
            "to a model your key can use, then restart the app."
        )
    return f"The AI service rejected the request (code {error.code}). Try rewording it."


def parse_json(raw_text):
    """Turn the model's text into a Python dict, tolerating stray Markdown fences."""
    text = raw_text.strip()
    if text.startswith("```"):
        # Drop a ```json ... ``` wrapper if the model added one.
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:]

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Last resort: keep only the outermost {...} block.
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise RecommendationError(
        "The AI's reply wasn't valid JSON, so it couldn't be read. Try again."
    )


def _to_int(value):
    """Convert ints, floats, and numeric strings like '2019' or '92%' to int."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        cleaned = value.strip().rstrip("%").strip()
        try:
            return int(float(cleaned))
        except ValueError:
            return None
    return None


def validate_movie(item):
    """Return a cleaned movie dict, or None if the item is unusable."""
    if not isinstance(item, dict):
        return None

    movie = {}
    for field in TEXT_FIELDS:
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            return None
        movie[field] = value.strip()

    year = _to_int(item.get("year"))
    if year is None or not 1880 <= year <= 2100:
        return None
    movie["year"] = year

    score = _to_int(item.get("match_score"))
    movie["match_score"] = max(0, min(100, score if score is not None else 0))
    return movie


def validate_recommendations(data, count, min_year=None, max_year=None):
    """Check the parsed JSON and return a clean, de-duplicated list of movies."""
    if not isinstance(data, dict) or not isinstance(data.get("recommendations"), list):
        raise RecommendationError(
            "The AI's reply didn't have the expected format. Try again."
        )

    movies = []
    seen_titles = set()
    for item in data["recommendations"]:
        movie = validate_movie(item)
        if movie is None:
            continue
        if min_year and movie["year"] < min_year:
            continue
        if max_year and movie["year"] > max_year:
            continue
        key = movie["title"].casefold()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        movies.append(movie)

    if not movies:
        raise RecommendationError(
            "The AI didn't return any usable recommendations. Try rephrasing "
            "your request or widening the year range."
        )

    movies.sort(key=lambda movie: movie["match_score"], reverse=True)
    return movies[:count]


def get_recommendations(user_request, count=5, genre="Any", min_year=None, max_year=None):
    """Main entry point: validate input, ask the AI, and return clean results."""
    if not user_request or not user_request.strip():
        raise RecommendationError("Describe the kind of movie you want first.")

    api_key = get_api_key()
    prompt = build_prompt(user_request, count, genre, min_year, max_year)
    raw_text = call_ai(prompt, api_key)
    data = parse_json(raw_text)
    return validate_recommendations(data, count, min_year, max_year)
