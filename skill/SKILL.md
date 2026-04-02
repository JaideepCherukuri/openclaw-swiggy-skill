---
name: swiggy-agent-runtime
description: Harden and evolve the Swiggy Telegram bot into a production-grade agent runtime. Use when designing or editing routing, planner/verifier logic, deterministic commerce workflows, tool-use policies, memory-commerce isolation, or runtime architecture for food, dineout, Instamart, memory, and utility turns.
---

# Swiggy Agent Runtime

Use this skill when working on the bot's execution model, not just one-off bug patches.

Read `references/runtime-architecture.md` before major runtime changes.

## 🚨 OPERATIONAL PLAYBOOK (HOW TO USE THE TOOLS) 🚨

**CRITICAL RULE FOR AGENTS:** Do NOT run `swiggy_unified_mcp.py` via shell `exec` or `python3` to search for products. It is a background MCP server, NOT a CLI script. It is automatically registered in OpenClaw. You must use your native tool-calling capability to execute `search_products`, `get_addresses`, `search_restaurants`, etc.

When a user asks you to search or order something on Swiggy, strictly follow these deterministic sequences:

### For Instamart (Groceries, Daily Needs):
1. **Get Address:** Call the `get_addresses` tool. Identify the correct `addressId` for the user's location. (Mandatory: Do NOT skip this).
2. **Search:** Call the `search_products` tool with `query="<user_query>"` and `addressId="<the_id>"`.
3. **Present:** Surface the results using the Presentation Playbook rules below.
4. **Cart:** To add to cart, use `update_cart`.

### For Food (Restaurant Delivery):
1. **Get Address:** Call the `get_addresses` tool. Identify the correct `addressId`. (Mandatory).
2. **Search:** Call the `search_restaurants` tool with `query="<user_query>"` and `addressId="<the_id>"`.
3. **Present:** Surface the results using the Presentation Playbook rules below.
4. **Menu:** If the user selects a restaurant, use `search_menu` with `restaurantId`.

### For Dineout (Table Booking):
1. **Get Address:** Call the `get_addresses` tool. Identify the correct `addressId`.
2. **Search:** Call the `search_restaurants_dineout` tool with `query="<user_query>"` (e.g., "lunch", "brewery", or specific name) and the coordinates derived from the address.
3. **Present:** Surface the results using the Presentation Playbook rules below.

---

## Core stance

Treat the bot as an agent runtime with layers, not as a single prompt with tools.

Default stack:
1. route the turn
2. short-circuit brittle deterministic flows
3. let the model plan only inside the allowed lane
4. execute tools with preserved structured state
5. verify the reply against the user ask and tool evidence

## Use this workflow

### 1. Classify the turn first
Assign one dominant domain before changing tool behavior:
- memory
- utility
- food exact
- food broad
- food menu follow-up
- dineout broad
- dineout booking follow-up
- instamart search
- instamart selection
- smalltalk
- general

If a turn is clearly `memory`, `utility`, or `smalltalk`, do not let stale commerce state hijack it.

### 2. Prefer deterministic control for brittle paths
Do not hand these directly to the model loop unless there is no reliable controller:
- exact restaurant or chain lookups
- nearby brand asks
- menu follow-ups
- Instamart selection and quantity steps
- stale Instamart reset on banter/greetings
- dineout locality refinements
- dineout booking follow-ups
- time/date asks

### 3. Keep state buckets separate
Maintain separate buckets for:
- memory
- food
- dineout
- instamart
- session meta

Never let autobiographical memory answers depend on commerce workflow state.
Never let casual chat resume an old cart or variant-selection flow.

### 4. Add a verifier before reply
Before shipping a reply, check:
- did we answer the exact user ask?
- if a brand was named, is the answer still scoped to that brand?
- if we mention availability/open status, do we have tool evidence?
- did we leak stale state from another domain?
- are we returning a broad shortlist when the user asked for an exact entity?
- **PRESENTATION CHECK (HARD RULE):** If showing food items, restaurants, or dineout options, does the message include ALL of the following?
  1. Compressed Image attached via `media` (using ffmpeg)
  2. Rating and Offers/Deals explicitly in the text
  3. Actionable CTA Buttons (Add to Cart / Book a Table)
  *Never send a naked text list if tool data contains images, deals, or actionable IDs.*

### 5. Use the model narrowly
The model should choose among valid actions in a known lane. Do not ask it to freestyle end-to-end workflow control for constrained commerce tasks.

Good model-owned work:
- soft paraphrase
- ranking/explanation once candidate set is grounded
- low-risk clarification questions
- general chat outside deterministic flows

Bad model-owned work:
- exact entity resolution without guardrails
- multi-turn variant selection
- implicit state recovery after degraded tools
- time/date answers
- mixing memory recall with current commerce context

### 6. Presentation Playbook (Formatting & UX)

**CRITICAL EXECUTION NOTE:** You MUST strictly follow these formatting rules. A naked text-only list for restaurants or menu items is considered a failure. Never skip images, deals, or interactive buttons.

Follow these strict rules when presenting options to the user:

**A. Volume & Streaming:**
- Always present at least **4-5 options** when the user asks for choices (unless fewer exist).
- Do not dump all options into a single massive message block. **Stream them one by one** (send separate messages for each option) so the user can easily evaluate and interact with them natively.
- **Suggestion Preferences:** When curating which options to surface, prefer restaurants that are **open**, prefer menu items that have **images** available, and prefer items that are **in stock**. (These are soft preferences, not hard filters; ignore them if the user specifically asks otherwise).
- **Unavailable Items:** If the user asks for a specific item or restaurant and it is unavailable or out of stock, explicitly inform them and then immediately surface **relevant, available alternatives** instead.

**B. Images & Compression:**
- Always show options with images if the tool payload includes an image URL.
- Before sending, download the image locally (`curl -s -o /tmp/img.png URL`) and compress it using `ffmpeg` to avoid API attachment limits (e.g., `ffmpeg -i /tmp/img.png -vf scale=800:-1 -q:v 8 /tmp/img_small.jpg -y`).
- Only send the compressed version using the `media` parameter in the `message` tool (e.g., `media: "/tmp/img_small.jpg"`). **NEVER use `buffer` with base64 interpolation (like `$(base64...)`) for images. The `buffer` field will drop the image.**

**C. Essential Data (Ratings & Offers):**
- **Food Menu Items:** Explicitly surface the rating alongside the item name and price.
- **Restaurants & Dineout:** Explicitly display their overall rating and any active discount offers.

**D. Channel-Agnostic CTA Buttons:**
- Always include interactive Call-to-Action (CTA) elements mapped to the native platform. Do not restrict this to Telegram.
- Use the `message` tool's `buttons` or `interactive` parameter. The gateway will automatically translate this into Telegram inline buttons, WhatsApp interactive lists, or Slack blocks.
- For Food/Instamart items, include an "Add to Cart 🛒" button (e.g., `callback_data: "/add <id>"`).
- For Dineout restaurants, include a "Book a Table 📅" button (e.g., `callback_data: "/book <id>"`).

## OpenClaw Playbook: Headless Authentication & Login

When an OpenClaw agent needs to authenticate to the Swiggy MCP servers, the agent must bridge the headless OAuth flow. 

You have two options for completing this flow. **Prefer Option 1 (Zero-Click) for a better UX**, but fall back to Option 2 if Playwright is unavailable or the flow fails.

### Option 1: Zero-Click Automation (Preferred)
Use the automated Playwright script to handle the login entirely on the agent side.
1. Run the MCP login script (`python3 ~/.openclaw/skills/openclaw-swiggy-skill/scripts/swiggy_unified_mcp_login.py`) in the background to generate the Auth URL.
2. Ask the user for their 10-digit Swiggy phone number.
3. Run the automation script: `python3 ~/.openclaw/skills/openclaw-swiggy-skill/scripts/swiggy_playwright_auth.py --url "AUTH_URL" --phone "PHONE_NUMBER"`.
4. The script will navigate Swiggy and ask for an OTP via `stdin`. Ping the user for the OTP, and pipe it in. The script will automatically intercept the `localhost` redirect and hit the callback server.

### Option 2: Manual Callback Paste (Fallback)
If the user prefers manual login or automation fails, use the manual copy-paste method:
1. Run the MCP auth script (`python3 ~/.openclaw/skills/openclaw-swiggy-skill/scripts/swiggy_unified_mcp_login.py`) in the background to generate the Auth URL.
2. Send the `https://mcp.swiggy.com/auth/...` URL to the user in chat.
3. Tell the user: *"Please click this link, log in, and enter your OTP. After successful login, your browser will try to load a broken `http://localhost:39025/...` or `http://127.0.0.1...` page. Copy that entire broken URL from your address bar and paste it back here."*
4. Once the user pastes the callback URL, run `curl "THE_PASTED_URL"` on the agent side to complete the loop.

## Editing guidance

When fixing a bug, prefer this order:
1. identify the domain and failure seam
2. decide whether it is router, controller, planner, executor, verifier, or state persistence
3. patch the smallest correct layer
4. add a regression test using the real runtime seam when possible
5. verify live behavior after deploy

Do not stack random heuristics if the real issue is missing architecture. If a heuristic is necessary, place it behind a named domain/controller rule and document why.

## Expected outputs

For architecture work, produce one or more of:
- explicit router decision table
- planner action schema
- verifier checklist in code
- extracted domain modules
- regression tests for the exact failure path
- state persistence fixes

## Reference

Use `references/runtime-architecture.md` for the target layering, state model, hard rules, and implementation order.
