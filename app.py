"""Streamlit interface for the AI Movie Recommender."""

import datetime

import streamlit as st

from ai import RecommendationError, get_recommendations

GENRES = ["Any", "Action", "Comedy", "Drama", "Horror", "Romance", "Sci-Fi", "Thriller", "Animation"]
COUNT_OPTIONS = [3, 5, 10]
EARLIEST_YEAR = 1900
CURRENT_YEAR = datetime.date.today().year


def render_header():
    st.title("🎬 AI Movie Recommender")
    st.markdown(
        "Tell me what you're in the mood for, and I'll find movies you'll probably enjoy."
    )


def render_inputs():
    """Draw the input widgets and return the user's choices as a dict."""
    user_request = st.text_area(
        "What kind of movie are you looking for?",
        height=140,
        placeholder=(
            "e.g. A funny action movie with a smart main character, "
            "preferably from the last 10 years."
        ),
    )

    col_count, col_genre = st.columns(2)
    with col_count:
        count = st.selectbox("Number of recommendations", COUNT_OPTIONS, index=1)
    with col_genre:
        genre = st.selectbox("Genre (optional)", GENRES)

    min_year, max_year = None, None
    if st.checkbox("Limit release years"):
        col_min, col_max = st.columns(2)
        with col_min:
            min_year = st.number_input(
                "From year", EARLIEST_YEAR, CURRENT_YEAR, value=CURRENT_YEAR - 10, step=1
            )
        with col_max:
            max_year = st.number_input(
                "To year", EARLIEST_YEAR, CURRENT_YEAR, value=CURRENT_YEAR, step=1
            )

    return {
        "user_request": user_request,
        "count": count,
        "genre": genre,
        "min_year": int(min_year) if min_year else None,
        "max_year": int(max_year) if max_year else None,
    }


def render_movie_card(movie):
    """Show one recommendation inside a bordered card."""
    with st.container(border=True):
        st.markdown(f"### 🎬 {movie['title']}")
        st.markdown(f"**{movie['year']} · {movie['genre']}**")
        st.markdown(f"> {movie['description']}")
        st.markdown("**Why you'll like it:**")
        st.write(movie["why_recommended"])
        st.progress(movie["match_score"] / 100, text=f"**Match:** {movie['match_score']}%")


def main():
    st.set_page_config(page_title="AI Movie Recommender", page_icon="🎬", layout="centered")
    render_header()
    choices = render_inputs()

    if st.button("Recommend Movies", type="primary", width="stretch"):
        if choices["min_year"] and choices["max_year"] and choices["min_year"] > choices["max_year"]:
            st.warning("\"From year\" must be the same as or earlier than \"To year\".")
        elif not choices["user_request"].strip():
            st.warning("Describe the kind of movie you want first.")
        else:
            with st.spinner("Finding movies for you..."):
                try:
                    st.session_state.movies = get_recommendations(**choices)
                    st.session_state.error = None
                except RecommendationError as error:
                    st.session_state.movies = []
                    st.session_state.error = str(error)
                except Exception:
                    # Safety net: never show a raw traceback to the user.
                    st.session_state.movies = []
                    st.session_state.error = "Something unexpected went wrong. Try again."

    # Results live in session_state so they survive Streamlit reruns.
    if st.session_state.get("error"):
        st.error(st.session_state.error)

    movies = st.session_state.get("movies") or []
    if movies:
        st.subheader("Recommended for you")
        if len(movies) < choices["count"]:
            st.caption(
                "Some suggestions were dropped because they were duplicates, "
                "incomplete, or outside your year range."
            )
        for movie in movies:
            render_movie_card(movie)
        st.caption(
            "Recommendations come from the AI's general knowledge, not a live movie "
            "database. Double-check details like release years before relying on them."
        )


if __name__ == "__main__":
    main()
