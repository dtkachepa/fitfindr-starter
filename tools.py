"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()

_STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "i",
    "in",
    "looking",
    "need",
    "of",
    "or",
    "the",
    "to",
    "under",
    "want",
    "with",
}


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    return {
        token
        for token in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower())
        if token not in _STOPWORDS
    }


def _listing_search_text(listing: dict) -> str:
    fields = [
        listing.get("title"),
        listing.get("description"),
        listing.get("category"),
        listing.get("brand"),
        " ".join(listing.get("style_tags") or []),
        " ".join(listing.get("colors") or []),
    ]
    return " ".join(str(field) for field in fields if field)


def _size_matches(requested_size: str | None, listing_size: str | None) -> bool:
    if requested_size is None or str(requested_size).strip() == "":
        return True
    if not listing_size:
        return False

    requested = str(requested_size).strip().lower()
    listed = str(listing_size).strip().lower()
    requested_tokens = _tokenize(requested)
    listed_tokens = _tokenize(listed)

    if requested == listed:
        return True

    clothing_sizes = {"xxs", "xs", "s", "m", "l", "xl", "xxl"}
    if requested in clothing_sizes:
        return requested in listed_tokens

    if requested_tokens and requested_tokens.issubset(listed_tokens):
        return True

    return False


def _format_item_name(item: dict) -> str:
    return item.get("title") or item.get("name") or "this item"


def _format_colors(colors: list[str] | None) -> str:
    if not colors:
        return "neutral"
    if len(colors) == 1:
        return colors[0]
    return ", ".join(colors[:-1]) + f", and {colors[-1]}"


def _vibe_from_tags(tags: list[str] | None) -> str:
    if not tags:
        return "easy everyday"
    return " ".join(tags[:3])


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()
    query = (description or "").strip()
    query_tokens = _tokenize(query)
    has_text_query = bool(query_tokens)
    scored_listings = []

    try:
        price_ceiling = float(max_price) if max_price is not None else None
    except (TypeError, ValueError):
        return []

    for listing in listings:
        if price_ceiling is not None and float(listing.get("price", 0)) > price_ceiling:
            continue
        if not _size_matches(size, listing.get("size")):
            continue

        search_text = _listing_search_text(listing)
        search_tokens = _tokenize(search_text)
        overlap = query_tokens & search_tokens
        score = len(overlap)

        title = str(listing.get("title") or "").lower()
        full_text = search_text.lower()
        if query and query.lower() in title:
            score += 5
        elif query and query.lower() in full_text:
            score += 3

        if query_tokens & _tokenize(listing.get("title")):
            score += 2

        if has_text_query and score <= 0:
            continue

        scored_listings.append((score, -float(listing.get("price", 0)), listing))

    scored_listings.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [listing for _, _, listing in scored_listings]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    if not isinstance(new_item, dict) or not new_item:
        return "I need a selected item before I can suggest an outfit."

    item_name = _format_item_name(new_item)
    item_category = new_item.get("category")
    item_colors = new_item.get("colors") or []
    item_tags = new_item.get("style_tags") or []
    wardrobe_items = []
    if isinstance(wardrobe, dict):
        wardrobe_items = wardrobe.get("items") or []

    if not wardrobe_items:
        vibe = _vibe_from_tags(item_tags)
        colors = _format_colors(item_colors)
        return (
            "Wardrobe context is limited because there are no saved wardrobe "
            f"items yet. Style {item_name} around its {colors} palette with "
            f"simple basics, one grounding shoe, and accessories that lean into "
            f"the {vibe} vibe."
        )

    needed_categories = {
        "tops": ["bottoms", "outerwear", "shoes", "accessories"],
        "bottoms": ["tops", "outerwear", "shoes", "accessories"],
        "outerwear": ["tops", "bottoms", "shoes", "accessories"],
        "shoes": ["tops", "bottoms", "outerwear", "accessories"],
        "accessories": ["tops", "bottoms", "outerwear", "shoes"],
    }.get(item_category, ["tops", "bottoms", "outerwear", "shoes", "accessories"])

    item_tag_set = set(item_tags)
    item_color_set = set(item_colors)

    def score_wardrobe_item(piece: dict) -> tuple[int, str]:
        category_score = 4 if piece.get("category") in needed_categories else 0
        tag_score = len(item_tag_set & set(piece.get("style_tags") or [])) * 2
        color_score = len(item_color_set & set(piece.get("colors") or []))
        notes_score = 1 if piece.get("notes") else 0
        return category_score + tag_score + color_score + notes_score, piece.get("name", "")

    ranked = sorted(wardrobe_items, key=score_wardrobe_item, reverse=True)
    selected = []
    used_categories = set()
    for piece in ranked:
        category = piece.get("category")
        if category == item_category:
            continue
        if category in used_categories and len(selected) >= 2:
            continue
        selected.append(piece)
        used_categories.add(category)
        if len(selected) == 3:
            break

    if not selected:
        selected = ranked[:2]

    piece_names = [piece.get("name", "an existing wardrobe piece") for piece in selected]
    colors = _format_colors(item_colors)
    vibe = _vibe_from_tags(item_tags)
    outfit_line = ", ".join(piece_names)
    return (
        f"Build the outfit around {item_name}. Pair it with {outfit_line} "
        f"to echo the {vibe} vibe while balancing the {colors} color story. "
        "Keep the rest of the styling simple so the thrifted piece feels intentional."
    )


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not isinstance(outfit, str) or not outfit.strip():
        return "I need an outfit suggestion before I can create a fit card."
    if not isinstance(new_item, dict) or not new_item:
        return "I need a selected item before I can create a fit card."

    item_name = _format_item_name(new_item)
    price = new_item.get("price")
    platform = new_item.get("platform")
    vibe = _vibe_from_tags(new_item.get("style_tags") or [])

    source_bits = []
    if price is not None:
        source_bits.append(f"${float(price):.0f}")
    if platform:
        source_bits.append(str(platform))
    source = " from ".join(source_bits) if len(source_bits) == 2 else " ".join(source_bits)
    source_phrase = f" ({source})" if source else ""

    return (
        f"FitFindr find: {item_name}{source_phrase}. Styled with pieces I already own "
        f"for a {vibe} look that feels pulled together without trying too hard. "
        "Secondhand score, full outfit energy."
    )
