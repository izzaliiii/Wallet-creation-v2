# Phase 1 — Extension reconnaissance

## Confirmed from the user's Chrome screenshot

- Product label: Jupiter Wallet
- Extension ID shown in the address bar: `iledlaeogohbilgbfhmbgkgmpplbfboh`
- Route: `chrome-extension://iledlaeogohbilgbfhmbgkgmpplbfboh/popup.html#/onboard`
- Welcome heading: "Welcome to Jupiter Wallet"
- Subtitle: "Your personal portal into Solana"
- Primary action: "Create a new wallet"
- Secondary action: "Import an existing wallet"
- Additional link: "Sync wallets"

## Scope decision

The current workflow covers creating a new personal wallet only. Import and sync are separate flows and are not automated by this project.

## Current checkpoint

The welcome/onboarding screen is visually confirmed. The screenshot does not establish:
- the DOM structure or accessible roles/names;
- the next screen after selecting Create a new wallet;
- whether a recovery phrase is shown, and how its confirmation works;
- password creation or unlock requirements;
- the exact point at which the public address becomes visible.

Do not infer selectors or automate the primary action based only on a screenshot.

## Next reconnaissance action

Run:

```powershell
python inspect_extension.py
```

The script launches the configured dedicated Chromium profile, opens the extension route, reports visible text and button/link/input metadata, and saves a screenshot. It does not click any onboarding control or read hidden extension storage.

Then inspect the DOM output and proceed manually through the provider UI, capturing each screen with secrets fully obscured. Never send recovery phrases, private keys, passwords, or QR codes.
