"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict | None = None) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query, kept for starter compatibility
        "user_query": query,         # original user query used by the Milestone 4 state flow
        "parsed": {},                # extracted description / size / max_price
        "description": None,         # parsed item description
        "size": None,                # parsed requested size
        "max_price": None,           # parsed price ceiling
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
        "error_message": None,       # user-facing error, kept in sync with error
        "completed_steps": [],       # tool steps completed by the planning loop
    }


def _parse_query(query: str) -> dict:
    """Extract the simple search fields needed by search_listings()."""
    text = (query or "").strip()
    lower_text = text.lower()

    max_price = None
    price_match = re.search(
        r"\b(?:under|below|max(?:imum)?|up to|less than)\s*\$?\s*(\d+(?:\.\d+)?)",
        lower_text,
    )
    if not price_match:
        price_match = re.search(r"\$(\d+(?:\.\d+)?)", lower_text)
    if price_match:
        max_price = float(price_match.group(1))

    size = None
    size_match = re.search(
        r"\b(?:in\s+)?size\s+"
        r"(xxs|xs|s|m|l|xl|xxl|extra\s+small|small|medium|large|extra\s+large|"
        r"us\s*\d+(?:\.\d+)?|w\d+(?:\s*l\d+)?)\b",
        lower_text,
    )
    if not size_match:
        size_match = re.search(r"\b(us\s*\d+(?:\.\d+)?|w\d+(?:\s*l\d+)?)\b", lower_text)
    if size_match:
        raw_size = re.sub(r"\s+", " ", size_match.group(1).strip())
        size_map = {
            "extra small": "XS",
            "small": "S",
            "medium": "M",
            "large": "L",
            "extra large": "XL",
        }
        size = size_map.get(raw_size, raw_size.upper())

    description = text
    description = re.split(
        r"\b(?:i mostly wear|what's out there|what is out there|how would i style|"
        r"how can i style|how would you style|style it)\b",
        description,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    description = re.sub(
        r"\b(?:under|below|max(?:imum)?|up to|less than)\s*\$?\s*\d+(?:\.\d+)?",
        " ",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(r"\$\d+(?:\.\d+)?", " ", description)
    description = re.sub(
        r"\b(?:in\s+)?size\s+"
        r"(?:xxs|xs|s|m|l|xl|xxl|extra\s+small|small|medium|large|extra\s+large|"
        r"us\s*\d+(?:\.\d+)?|w\d+(?:\s*l\d+)?)\b",
        " ",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(
        r"\b(?:i'?m|i am|looking for|searching for|trying to find|find me|"
        r"need|want|a|an|some|please)\b",
        " ",
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(r"[^\w\s/-]", " ", description)
    description = re.sub(r"\s+", " ", description).strip()

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


def _set_error(session: dict, message: str) -> None:
    session["error"] = message
    session["error_message"] = message


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(session: dict | str | None = None, wardrobe: dict | None = None, query: str | None = None) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    if isinstance(session, dict):
        session_state = session
        user_query = session_state.get("user_query") or session_state.get("query") or ""
    else:
        user_query = query if query is not None else (session or "")
        session_state = _new_session(str(user_query), wardrobe)

    session_state.setdefault("query", user_query)
    session_state.setdefault("user_query", user_query)
    session_state.setdefault("parsed", {})
    session_state["search_results"] = []
    session_state["selected_item"] = None
    session_state["outfit_suggestion"] = None
    session_state["fit_card"] = None
    session_state["completed_steps"] = []
    session_state["error"] = None
    session_state["error_message"] = None

    parsed = _parse_query(str(user_query))
    explicit_fields = {
        "description": session_state.get("description"),
        "size": session_state.get("size"),
        "max_price": session_state.get("max_price"),
    }
    parsed.update({key: value for key, value in explicit_fields.items() if value not in (None, "")})

    session_state["parsed"] = parsed
    session_state["description"] = parsed.get("description")
    session_state["size"] = parsed.get("size")
    session_state["max_price"] = parsed.get("max_price")

    if not session_state.get("description"):
        _set_error(session_state, "Tell me what kind of secondhand item you want to find.")
        return session_state

    if not session_state.get("wardrobe"):
        session_state["wardrobe"] = get_example_wardrobe()

    results = search_listings(
        session_state["description"],
        session_state.get("size"),
        session_state.get("max_price"),
    )
    session_state["search_results"] = results
    session_state["completed_steps"].append("search_listings")

    if not results:
        session_state["selected_item"] = None
        session_state["outfit_suggestion"] = None
        session_state["fit_card"] = None
        _set_error(
            session_state,
            "No listings matched that request. Try a broader item description, a different size, or a higher max price.",
        )
        print(f"completed_steps: {session_state['completed_steps']}")
        return session_state

    selected_item = results[0]
    session_state["selected_item"] = selected_item
    print(f"selected_item: {selected_item}")

    outfit_suggestion = suggest_outfit(selected_item, session_state["wardrobe"])
    session_state["outfit_suggestion"] = outfit_suggestion
    session_state["completed_steps"].append("suggest_outfit")
    print(f"outfit_suggestion: {outfit_suggestion}")

    if not isinstance(outfit_suggestion, str) or not outfit_suggestion.strip():
        session_state["fit_card"] = None
        _set_error(session_state, "I found a listing, but could not create an outfit suggestion for it.")
        print(f"completed_steps: {session_state['completed_steps']}")
        return session_state

    fit_card = create_fit_card(outfit_suggestion, selected_item)
    session_state["fit_card"] = fit_card
    session_state["completed_steps"].append("create_fit_card")
    print(f"fit_card: {fit_card}")
    print(f"completed_steps: {session_state['completed_steps']}")

    return session_state


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
