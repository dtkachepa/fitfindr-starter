import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import run_agent
from app import handle_query
from utils.data_loader import get_example_wardrobe


SUCCESS_QUERY = (
    "I'm looking for a vintage graphic tee in size M under $30. "
    "I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"
)


def test_run_agent_successful_full_path():
    session = {
        "user_query": SUCCESS_QUERY,
        "wardrobe": get_example_wardrobe(),
        "completed_steps": [],
    }

    result = run_agent(session)

    assert result["error"] is None
    assert result["error_message"] is None
    assert result["description"] == "vintage graphic tee"
    assert result["size"] == "M"
    assert result["max_price"] == 30.0
    assert result["search_results"]
    assert result["selected_item"] == result["search_results"][0]
    assert result["outfit_suggestion"]
    assert result["fit_card"]
    assert result["completed_steps"] == [
        "search_listings",
        "suggest_outfit",
        "create_fit_card",
    ]


def test_run_agent_stops_early_when_search_has_no_results():
    session = {
        "user_query": "I'm looking for a designer ballgown in size XXS under $5.",
        "wardrobe": get_example_wardrobe(),
        "completed_steps": [],
    }

    result = run_agent(session)

    assert result["search_results"] == []
    assert result["selected_item"] is None
    assert result["outfit_suggestion"] is None
    assert result["fit_card"] is None
    assert "No listings matched" in result["error"]
    assert "broader item description" in result["error"]
    assert result["completed_steps"] == ["search_listings"]
    assert "suggest_outfit" not in result["completed_steps"]
    assert "create_fit_card" not in result["completed_steps"]


def test_handle_query_success_outputs_three_panels():
    listing_text, outfit_text, fit_card_text = handle_query(SUCCESS_QUERY, "Example wardrobe")

    assert "Y2K Baby Tee" in listing_text
    assert "Platform:" in listing_text
    assert outfit_text
    assert fit_card_text


def test_handle_query_no_results_outputs_error_only():
    listing_text, outfit_text, fit_card_text = handle_query(
        "I'm looking for a designer ballgown in size XXS under $5.",
        "Example wardrobe",
    )

    assert "No listing was selected" in listing_text
    assert "No listings matched" in listing_text
    assert "broader item description" in listing_text
    assert outfit_text == ""
    assert fit_card_text == ""
