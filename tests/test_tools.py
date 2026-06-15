import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


def test_search_listings_returns_relevant_results():
    results = search_listings("vintage graphic tee", None, 30.0)

    assert results
    assert any(item["id"] in {"lst_002", "lst_006", "lst_033"} for item in results)


def test_search_listings_no_results_for_impossible_constraints():
    results = search_listings("designer ballgown", size="XXS", max_price=5)

    assert results == []


def test_search_listings_applies_price_filter():
    max_price = 45.0
    results = search_listings("jacket", None, max_price)

    assert results
    assert all(item["price"] <= max_price for item in results)


def test_search_listings_size_m_does_not_return_l_only_items():
    results = search_listings("vintage graphic tee", "M", 30.0)

    assert results
    assert all(item["size"] != "L" for item in results)
    assert any(item["id"] == "lst_002" for item in results)


def test_suggest_outfit_with_example_wardrobe():
    new_item = search_listings("vintage graphic tee", "M", 30.0)[0]
    outfit = suggest_outfit(new_item, get_example_wardrobe())

    assert isinstance(outfit, str)
    assert new_item["title"] in outfit
    assert "wardrobe" not in outfit.lower() or "limited" not in outfit.lower()


def test_suggest_outfit_with_empty_wardrobe_returns_fallback():
    new_item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    outfit = suggest_outfit(new_item, get_empty_wardrobe())

    assert isinstance(outfit, str)
    assert outfit.strip()
    assert "limited" in outfit.lower() or "no saved wardrobe" in outfit.lower()
    assert new_item["title"] in outfit


def test_suggest_outfit_missing_new_item_returns_clear_message():
    outfit = suggest_outfit(None, get_example_wardrobe())

    assert "selected item" in outfit.lower()


def test_create_fit_card_with_valid_inputs():
    new_item = search_listings("vintage graphic tee", "M", 30.0)[0]
    outfit = suggest_outfit(new_item, get_example_wardrobe())
    fit_card = create_fit_card(outfit, new_item)

    assert isinstance(fit_card, str)
    assert new_item["title"] in fit_card
    assert str(int(new_item["price"])) in fit_card
    assert new_item["platform"] in fit_card


def test_create_fit_card_missing_outfit_returns_clear_message():
    new_item = search_listings("vintage graphic tee", size=None, max_price=50)[0]
    fit_card = create_fit_card("", new_item)

    assert isinstance(fit_card, str)
    assert "outfit suggestion" in fit_card.lower()
    assert "FitFindr find:" not in fit_card


def test_create_fit_card_missing_new_item_returns_clear_message():
    fit_card = create_fit_card("Wear it with jeans and sneakers.", None)

    assert "selected item" in fit_card.lower()
