# OpenClaw Swiggy Agent

A unified, multi-domain OpenClaw skill to interact with Swiggy through natural language using the [Swiggy MCP server](https://github.com/Swiggy/swiggy-mcp-server-manifest).

This single agent supports three distinct Swiggy ecosystems:
- **Swiggy Food** — search restaurants, browse menus, manage cart, place food orders (COD)
- **Instamart** — search products, cart, place grocery orders (COD)
- **Dineout** — discover restaurants, check slots, book tables (free bookings)

## ⚠️ Safety First

By design, this agent is given **strict instructions to never place an order without final consent**. 
It will build your cart, find your tables, and check slots—but it will ALWAYS stop and ask for your explicit confirmation before checking out or confirming a booking.

## Prerequisites

- [Node.js](https://nodejs.org/) >= 22
- [OpenClaw](https://github.com/openclaw/openclaw) installed and gateway running
- [mcporter](https://mcporter.dev) installed (`npm install -g mcporter`)
- A Swiggy account

## Quick Start

```bash
git clone https://github.com/JaideepCherukuri/openclaw-swiggy-instamart.git
cd openclaw-swiggy-instamart
chmod +x scripts/*.sh
./scripts/install.sh
```

The installer will:
1. Verify prerequisites
2. Copy the skill to `~/.openclaw/skills/swiggy-agent/`
3. Automatically configure `swiggy-food`, `swiggy-instamart`, and `swiggy-dineout` in `mcporter`.

## Authentication

You must authenticate each Swiggy domain you wish to use. Running these commands will open a browser window for Swiggy OAuth login:

```bash
# For Groceries
mcporter auth swiggy-instamart

# For Food Delivery
mcporter auth swiggy-food

# For Restaurant Reservations
mcporter auth swiggy-dineout
```

Verify it worked:
```bash
mcporter list
```

## Usage

Interact with the agent via OpenClaw:

```bash
# Food
openclaw agent -m "I want to order a Margherita pizza from a nearby Italian place."

# Instamart
openclaw agent -m "Add a dozen eggs and 500g of chicken breast to my Instamart cart."

# Dineout
openclaw agent -m "Book a table for 2 at a nice sushi restaurant tonight at 8 PM."
```

## Security

No secrets are stored in this repository. All API keys and tokens live in `~/.openclaw/.env` and are managed securely by the OpenClaw environment. 

See [docs/SECURITY.md](docs/SECURITY.md) for the full security model.

## License

[MIT](LICENSE)
