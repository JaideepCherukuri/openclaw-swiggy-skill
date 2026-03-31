---
name: swiggy-agent
description: Openclaw skill to place Swiggy orders through natural language using the Swiggy MCP. Supports Swiggy Food, Instamart, and Dineout.
---

# Swiggy Agent

A unified OpenClaw skill to interact with Swiggy across Food, Instamart, and Dineout.

## Domains & Capabilities

1. **Swiggy Food** (`swiggy-food`)
   - Search restaurants, browse menus, manage cart, place food orders (COD).
2. **Instamart** (`swiggy-instamart`)
   - Search products, manage cart, place grocery orders (COD).
3. **Dineout** (`swiggy-dineout`)
   - Discover restaurants, check available slots, book tables (free bookings).

## ⚠️ STRICT RULES & SECURITY (CRITICAL) ⚠️

1. **FINAL CONSENT REQUIRED:** DO NOT PLACE AN ORDER WITHOUT FINAL CONSENT. Explicitly ask the user for confirmation before calling any checkout, table booking, or order creation tools.
2. **NO ACCIDENTAL ORDERS DURING TESTING:** Even during unit tests or debugging, you MUST NOT place an order.
3. Use the `mcporter` CLI to interact with the respective MCP servers.
   - Example Food: `mcporter call swiggy-food.<tool> ...`
   - Example Instamart: `mcporter call swiggy-instamart.<tool> ...`
   - Example Dineout: `mcporter call swiggy-dineout.<tool> ...`
4. If authentication fails or expires, inform the user to re-authenticate using `mcporter auth <server_name>`.

## Example Workflows

### Food Order Flow (Requires final confirmation)
1. `mcporter call swiggy-food.get_addresses` to find the delivery address.
2. `mcporter call swiggy-food.search_restaurants` based on user's query.
3. `mcporter call swiggy-food.get_menu` to find items.
4. `mcporter call swiggy-food.update_cart` to add items to the cart.
5. **STOP and ask the user for confirmation.**
6. Once confirmed: `mcporter call swiggy-food.checkout` (or equivalent tool).

### Instamart Grocery Flow (Requires final confirmation)
1. `mcporter call swiggy-instamart.get_addresses` to find the delivery address.
2. `mcporter call swiggy-instamart.search_products` to find groceries.
3. `mcporter call swiggy-instamart.update_cart` to add products to the cart.
4. **STOP and ask the user for confirmation.**
5. Once confirmed: `mcporter call swiggy-instamart.checkout` (or equivalent).

### Dineout Booking Flow (Requires final confirmation)
1. `mcporter call swiggy-dineout.search_restaurants` to find places.
2. `mcporter call swiggy-dineout.get_slots` to check availability for the requested time/pax.
3. **STOP and ask the user for confirmation.**
4. Once confirmed: `mcporter call swiggy-dineout.book_table` (or equivalent tool).
