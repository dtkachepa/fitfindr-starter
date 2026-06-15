# FitFindr - planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation - the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed below.

### Tool 1: search_listings

**What it does:**
Searches the mock secondhand listings dataset for items that match the user's requested item description, optional size, and optional maximum price. It should use `load_listings()` from `utils/data_loader.py` and rank/filter against listing fields rather than re-reading JSON directly.

**Input parameters:**
- `description` (str): Natural language item request, such as `"vintage graphic tee"`, `"black leather jacket"`, or `"platform sneakers"`.
- `size` (str or null): Requested size, such as `"M"`, `"L"`, `"US 8"`, `"W30"`, or `null` when the user did not provide a size.
- `max_price` (float, int, or null): Maximum price the user wants to pay, such as `30.0`, or `null` when the user did not provide a budget.

**What it returns:**
A list of matching listing dictionaries from `data/listings.json`, sorted by relevance. Each item includes `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Current return type:

```python
list[dict]
```

Filtering and matching rules:

- If `max_price` is provided, only return listings where `price <= max_price`.
- If `size` is provided, prefer exact or close text matches against the listing `size` field.
- Use `title`, `description`, `category`, `style_tags`, `colors`, and `brand` for text relevance.
- Rank stronger text matches higher, then prefer items that satisfy size and price cleanly.

Success means the returned list contains at least one relevant listing. Failure/no-match means the returned list is empty (`[]`) after applying constraints or when the inputs are unusable.

**What happens if it fails or returns nothing:**
The agent should save the error in session state, tell the user no listings were found, name the likely narrow constraint such as size, description, or price, and stop before calling `suggest_outfit` or `create_fit_card`. The agent can ask the user to loosen constraints, for example by increasing max price or trying a broader description.

---

### Tool 2: suggest_outfit

**What it does:**
Suggests how to style one selected listing with the user's existing wardrobe. It should use the selected item's category, colors, and style tags, then choose compatible wardrobe pieces by category, color harmony, style overlap, and notes.

**Input parameters:**
- `new_item` (dict): One selected listing returned by `search_listings`. It should include at least `title`, `category`, `colors`, `style_tags`, `price`, and `platform`.
- `wardrobe` (dict): Wardrobe object from `get_example_wardrobe()` or `get_empty_wardrobe()`, with an `items` list.

**What it returns:**
A string containing the outfit suggestion.

Current return type:

```python
str
```

Success means the returned string is non-empty and gives usable styling guidance. If the wardrobe is empty or minimal, the tool still returns a non-empty fallback advice string that clearly says it has limited wardrobe context. If `new_item` is missing, it returns a clear message string instead of raising an exception.

**What happens if it fails or returns nothing:**
If `new_item` is missing or unusable, the agent should stop and ask the user to select an item first. If the wardrobe is empty, the agent should use fallback styling advice rather than stopping, then continue to `create_fit_card` only if an outfit suggestion exists.

---

### Tool 3: create_fit_card

**What it does:**
Creates a short shareable outfit caption from the selected listing and outfit suggestion. The caption should feel like an Instagram outfit post and mention the new item, price or platform when available, and styling vibe.

**Input parameters:**
- `outfit` (str): The outfit suggestion produced by `suggest_outfit`.
- `new_item` (dict): The selected listing returned by `search_listings`.

**What it returns:**
A string containing the short shareable caption / fit card.

Current return type:

```python
str
```

Success means the returned string is a caption based on the selected item and outfit suggestion. If `outfit` or `new_item` is missing, empty, or unusable, the tool returns a clear error message string instead of raising an exception.

**What happens if it fails or returns nothing:**
The agent should explain that it needs a selected item and outfit suggestion before it can create a fit card. It should not invent missing item details; it should ask the user to pick an item or rerun the outfit step.

---

### Additional Tools (if any)

No additional tools are planned for the required milestone flow. The agent should rely on `search_listings`, `suggest_outfit`, and `create_fit_card`.

---

## Planning Loop

**How does your agent decide which tool to call next?**

The agent should use session state to decide whether the next tool has the inputs it needs. It should not blindly call all tools in a fixed sequence.

1. Receive the user query and save it as `user_query`.
2. Parse or infer `description`, `size`, and `max_price` from the query. If the user does not provide `size`, store `null`; if the user does not provide `max_price`, store `null`.
3. Load or receive wardrobe context and save it as `wardrobe`. During early testing this can come from `get_example_wardrobe()` or `get_empty_wardrobe()`.
4. If the user is asking to find a secondhand item, call `search_listings(description, size, max_price)`.
5. Save the returned list as `search_results` and record `"search_listings"` in `completed_steps`.
6. If the returned list is empty, save `error_message`, tell the user no listings were found, suggest loosening size, description, or price constraints, and stop.
7. If listings are found, select the best item by relevance and price match, or use the first ranked result. Save it as `selected_item`.
8. Only if `selected_item` exists, call `suggest_outfit(selected_item, wardrobe)`.
9. Save the returned outfit as `outfit_suggestion` and record `"suggest_outfit"` in `completed_steps`.
10. If `suggest_outfit` returns an empty or unusable string, save `error_message`, ask the user to select an item, and stop.
11. If the wardrobe is empty, allow fallback styling advice if the tool returns a non-empty suggestion with limited wardrobe context.
12. Only if `outfit_suggestion` exists, call `create_fit_card(outfit_suggestion, selected_item)`.
13. Save the returned caption as `fit_card` and record `"create_fit_card"` in `completed_steps`.
14. Return a final response containing the selected listing, the outfit suggestion, and the fit card.

The loop is complete when it has either returned a final response with a selected listing, outfit, and fit card, or stopped early with a clear user-facing error message.

---

## State Management

**How does information from one tool get passed to the next?**

The agent should keep a session state dictionary for the current interaction. Each tool reads only the state it needs and writes back its actual return value for later steps.

| State key | Type | Purpose |
|-----------|------|---------|
| `user_query` | str | Original user request. |
| `description` | str or null | Parsed item description used by `search_listings`. |
| `size` | str or null | Parsed requested size; `null` means no size filter. |
| `max_price` | float/int or null | Parsed price ceiling; `null` means no price filter. |
| `wardrobe` | dict | User wardrobe object with an `items` list. |
| `search_results` | list[dict] | Listings returned by `search_listings`. |
| `selected_item` | dict or null | The listing chosen for styling. |
| `outfit_suggestion` | str or null | Output from `suggest_outfit`. |
| `fit_card` | str or null | Caption output from `create_fit_card`. |
| `error_message` | str or null | Current blocking error or user-facing failure explanation. |
| `completed_steps` | list[str] | Tool names that completed successfully or intentionally with fallback. |

Data flow:

- `user_query` is parsed into `description`, `size`, and `max_price`.
- `description`, `size`, and `max_price` are passed into `search_listings`.
- `search_results` is used to choose `selected_item`.
- `selected_item` and `wardrobe` are passed into `suggest_outfit`.
- `outfit_suggestion` and `selected_item` are passed into `create_fit_card`.
- `fit_card`, `outfit_suggestion`, and `selected_item` are combined into the final response.
- If any required state is missing, the agent should stop or use the documented fallback instead of continuing with invalid inputs.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool or step | Failure mode | Cause | Tool return | Agent response | Stop, retry, or fallback |
|--------------|--------------|-------|-------------|----------------|--------------------------|
| search_listings | No results match the query | Description, size, or max price is too narrow for the 40 mock listings. | `[]` | Tell the user no listings were found and suggest broadening the description, removing size, or increasing max price. | Stop before `suggest_outfit` and `create_fit_card`. |
| search_listings | User gives no size | Size was not included in the user query. | A `list[dict]` if description/price matches exist, with `size` treated as `None`. | Continue with the returned listings. | Continue; no retry needed. |
| search_listings | User gives no max price | Budget was not included in the user query. | A `list[dict]` if description/size matches exist, with `max_price` treated as `None`. | Continue with the returned listings. | Continue; no retry needed. |
| search_listings | Inputs are unusable | Description is empty or unrelated to finding an item. | Usually `[]` after no relevant matches. | Ask the user what kind of item they want to find. | Stop until user provides a clearer request. |
| suggest_outfit | Wardrobe is empty | `wardrobe["items"]` is empty, such as from `get_empty_wardrobe()`. | A non-empty fallback advice string mentioning limited wardrobe context. | Say wardrobe context is limited and style the new item with general advice. | Fallback and continue if the string is non-empty. |
| suggest_outfit | Selected item is missing | `selected_item` was not saved because search failed or no item was chosen. | A clear message string such as `I need a selected item before I can suggest an outfit.` | Ask the user to select a listing first. | Stop. |
| create_fit_card | Outfit suggestion is missing | `suggest_outfit` failed or was skipped. | A clear message string: `I need an outfit suggestion before I can create a fit card.` | Explain that a fit card needs an outfit suggestion first. | Stop. |
| create_fit_card | New item is missing | Selected listing is missing or malformed. | A clear message string such as `I need a selected item before I can create a fit card.` | Ask the user to choose a listing before creating the caption. | Stop. |

---

## Architecture

```mermaid
flowchart TD
    A[User query] --> B[Planning loop parses description, size, max_price, wardrobe context]
    B <--> S[(Session state)]
    B --> C{Is user asking to find an item?}
    C -- No --> Z[Respond normally or ask for a secondhand item request]
    C -- Yes --> D["search_listings(description, size, max_price)"]
    D --> S
    D --> E{Any matching listings?}
    E -- No --> F[Save error_message]
    F --> G[Tell user no listings were found and suggest loosening constraints]
    G --> H[Stop early]
    E -- Yes --> I[Select best ranked listing]
    I --> J[Save selected_item]
    J --> S
    J --> K{selected_item exists?}
    K -- No --> L[Ask user to select an item and stop]
    K -- Yes --> M["suggest_outfit(selected_item, wardrobe)"]
    M --> S
    M --> N{outfit_suggestion exists?}
    N -- No --> O[Explain outfit could not be created and stop]
    N -- Yes --> P["create_fit_card(outfit_suggestion, selected_item)"]
    P --> S
    P --> Q[Final response: selected listing, outfit suggestion, fit card]
```

---

## AI Tool Plan

For each implementation milestone, I will use Codex with the specific planning sections below instead of asking it to generate a whole agent from a vague prompt.

**Milestone 3 - Individual tool implementations:**

- For implementing `search_listings`, I will give Codex the Tool 1 specification, listings data fields, and `utils/data_loader.py` helper details. I expect Codex to implement filtering with `load_listings()` and return a ranked `list[dict]`, with `[]` for no-result behavior. I will verify it by testing matching queries, size filtering, price filtering, combined constraints, and no-result behavior.
- For implementing `suggest_outfit`, I will give Codex the Tool 2 specification, wardrobe schema, and `selected_item` state contract. I expect Codex to implement category-aware and style-aware outfit selection using wardrobe `category`, `colors`, `style_tags`, and `notes`. I will verify it with `get_example_wardrobe()` and `get_empty_wardrobe()` to confirm both normal and fallback behavior.
- For implementing `create_fit_card`, I will give Codex the Tool 3 specification and expected caption behavior. I expect Codex to produce short captions that mention the new item, price or platform when available, and the styling vibe. I will verify that valid inputs return a caption string and that missing `outfit` or `new_item` inputs return clear message strings.

**Milestone 4 - Planning loop and state management:**

- For implementing the planning loop, I will give Codex the Architecture diagram, Planning Loop section, and State Management section. I expect Codex to implement state transitions that only call downstream tools when the previous tool produced the required state. I will verify that the agent does not call `suggest_outfit` or `create_fit_card` when `search_listings` fails, and that successful runs return the selected listing, outfit suggestion, and fit card.

---

## A Complete Interaction (Step by Step)

FitFindr should help the user find a secondhand item, style it with pieces they already own, and turn the result into a short shareable fit caption. When the user asks for an item with constraints like description, size, or max price, the agent should call `search_listings`; after the user or agent selects a candidate item, it should call `suggest_outfit` with that item and the user's wardrobe; after an outfit is suggested, it should call `create_fit_card` to generate the caption. If `search_listings` finds no matches, the agent should explain what constraint likely blocked the search and stop or ask the user to loosen the constraints instead of calling `suggest_outfit` or `create_fit_card`.

Write out what a full user interaction looks like from start to finish - tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee in size M under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent parses the query and saves:

- `user_query`: `"I'm looking for a vintage graphic tee in size M under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"`
- `description`: `"vintage graphic tee"`
- `size`: `"M"`
- `max_price`: `30.0`
- `wardrobe`: the user's wardrobe, using `get_example_wardrobe()` during starter testing.

For user queries where no size is provided, the agent should store `size` as `null` and search without a size filter.

First tool call:

```text
search_listings(description="vintage graphic tee", size="M", max_price=30.0)
```

**Step 2:**
`search_listings` filters listings priced at or below `$30`, applies the size `"M"` constraint, and ranks text matches for `"vintage graphic tee"` using title, description, category, style tags, colors, and brand. Because the query asks for size M, the walkthrough should not treat size L tee listings as matches unless the agent intentionally asks the user to loosen the size constraint. A realistic compatible returned listing is:

- `lst_002`: `"Y2K Baby Tee - Butterfly Print"`, size `S/M`, price `$18.00`, platform `depop`. This is compatible with a size M query because the listing size explicitly includes `M`, and its title/description/style tags include tee, graphic, vintage, and Y2K signals.

The agent saves this as `search_results`, selects the best ranked result, and saves it as `selected_item`. For this walkthrough, `selected_item` is `lst_002`.

Second tool call:

```text
suggest_outfit(new_item=selected_item, wardrobe=wardrobe)
```

**Step 3:**
`suggest_outfit` uses the selected tee's category, white/pink/purple colors, and style tags such as `y2k`, `vintage`, `graphic tee`, and `cottagecore`. With the example wardrobe, it can pair the tee with baggy dark-wash jeans, chunky white sneakers, and the black crossbody bag. The agent saves this result as `outfit_suggestion`.

Third tool call:

```text
create_fit_card(outfit=outfit_suggestion, new_item=selected_item)
```

`create_fit_card` creates a short caption that mentions the selected listing, its price or platform, and the styling vibe. The agent saves the caption as `fit_card`.

**Error path if search returns no matches:**

If `search_listings("vintage graphic tee", "M", 30.0)` returns `[]`, the agent saves `error_message`, tells the user no matching size M tees were found under `$30`, suggests loosening the size, description, or price constraint, and stops without calling `suggest_outfit` or `create_fit_card`.

**Final output to user:**
The user sees one concise response with:

- Selected listing: `"Y2K Baby Tee - Butterfly Print"` from `depop`, size `S/M`, `$18.00`, condition `excellent`.
- Outfit suggestion: Wear it with baggy dark-wash jeans, chunky white sneakers, and a black crossbody bag for a Y2K vintage look.
- Fit card caption: `"Depop find: an $18 butterfly baby tee styled with baggy denim, chunky sneakers, and a black crossbody - soft Y2K vintage energy."`
