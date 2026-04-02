# Swiggy Zero-Click OAuth Playbook

When a user needs to authenticate to Swiggy (or re-authenticate because tokens expired), **do not ask them to copy and paste the localhost callback URL**. Instead, run an automated headless browser flow to complete the login seamlessly.

## Prerequisites
The agent must have `playwright` installed. If it is not installed, install it:
```bash
pip install playwright
playwright install chromium
```

## Step-by-Step Flow

1. **Ask for Phone Number:** Ask the user for their 10-digit Swiggy registered phone number.
2. **Start the MCP Login:** Run the Swiggy unified MCP login script in the background. This will print an Authorization URL (starting with `https://mcp.swiggy.com/auth/authorize?...`).
   ```bash
   python3 ~/.openclaw/skills/openclaw-swiggy-skill/scripts/swiggy_unified_mcp_login.py
   ```
3. **Run the Playwright Automator:** Run `swiggy_playwright_auth.py` and pass the URL and Phone Number:
   ```bash
   python3 ~/.openclaw/skills/openclaw-swiggy-skill/scripts/swiggy_playwright_auth.py --url "THE_AUTH_URL" --phone "1234567890"
   ```
4. **Wait for OTP Prompt:** The script will automatically navigate the consent screens, enter the phone number, and click send. It will pause and print `[ACTION_REQUIRED] Enter OTP: ` to stdout.
5. **Ask for OTP:** Once the script is waiting, ask the user for the OTP sent to their phone.
6. **Pass OTP to Script:** Write the 6-digit OTP into the `stdin` of the running script process.
7. **Complete:** The script will enter the OTP, bypass Swiggy's frontend redirect blockades, and hit the localhost callback automatically. The background MCP login script will receive the code and save the tokens.

## Why this exists
Swiggy's frontend explicitly blocks redirects to unknown URIs, which prevents smart tunneling hacks. However, it still allows `localhost`. But the browser doesn't automatically redirect if it's not whitelisted in their exact schema. The `swiggy_playwright_auth.py` script catches the `success=true` page URL, extracts the hidden `localhost` callback URI with the auth `code`, and triggers the local callback server directly. This gives the user a zero-click experience (only providing phone and OTP in chat).
