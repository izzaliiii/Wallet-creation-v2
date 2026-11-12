# Jupiter Wallet Bot

A local, CLI-based wallet provisioning assistant for a verified Jupiter Wallet browser extension. Built with Python, Playwright, SQLite, Argon2id and AES-256-GCM.

## Security model

- Browser onboarding is human-in-the-loop. The application opens the extension and pauses for the user to complete provider-controlled security steps.
- Recovery phrases and private keys are never read from browser storage, DOM internals, extension databases, or network traffic.
- The user may explicitly enter an exported secret into a hidden terminal prompt for encrypted local storage. This is optional.
- No CAPTCHA solving, password interception, transaction signing, account-limit evasion, or unattended wallet creation.
- The vault key is derived from a master password with Argon2id; encrypted records use AES-256-GCM with a fresh nonce.
- SQLite stores public metadata and ciphertext only. Keep the vault database and backups private.

## Requirements

- Python 3.11+
- Google Chrome or Chromium
- A locally installed, verified, unpacked Jupiter Wallet extension directory
- Windows, macOS, or Linux

## Setup (PowerShell)

```powershell
git clone https://github.com/izzaliiii/Wallet-creation-v2.git
cd Wallet-creation-v2
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set `CHROME_EXECUTABLE`, `EXTENSION_PATH`, and the extension ID after verifying the publisher and extension package yourself. Do not download an extension package from an untrusted source.

## First run

```powershell
python main.py start
python main.py add --name "Personal Wallet 1" --network "Solana"
python main.py queue
python main.py process
```

The first vault operation prompts you to create a master password. Use a strong, unique password and keep it in a password manager. The application cannot recover it.

During `process`, the app launches a dedicated persistent Chromium profile with the unpacked extension enabled. Complete the wallet provider's onboarding and security prompts yourself. When the app asks, enter the public address shown by the wallet. The app does not claim creation succeeded until the user confirms the address and it passes basic format/non-duplicate checks.

## CLI

| Command | Purpose |
|---|---|
| `python main.py start` | Initialize database and check configuration |
| `python main.py add --name NAME --network NETWORK` | Add a queue request |
| `python main.py queue` | Show queue |
| `python main.py process` | Process pending requests sequentially |
| `python main.py list` | List saved wallet metadata |
| `python main.py details --id ID` | Show wallet metadata |
| `python main.py retrieve --id ID` | Explicitly decrypt and display a stored secret |
| `python main.py verify --id ID` | Re-open extension and let the user verify wallet access |
| `python main.py backup` | Create an encrypted database backup |
| `python main.py restore --file PATH` | Authenticate and restore an encrypted `.jwbak` backup |
| `python main.py lock` | Lock the in-memory vault key |

## Extension reconnaissance

After configuring `.env`, run `python inspect_extension.py` to inspect the visible onboarding DOM without clicking any wallet action. The script saves a screenshot under the local data directory's `reconnaissance/` folder. See [`docs/extension-reconnaissance.md`](docs/extension-reconnaissance.md) for the confirmed welcome-screen observations.


The extension ID supplied during planning was `iledlaeogohbilgbfhmbgkgmpplbfboh`. Treat this as an unverified configuration value until you confirm the extension publisher and ID in Chrome. The actual onboarding selectors and routes must be inspected against the installed extension version. This initial implementation intentionally avoids brittle guessed selectors.

## Data locations

By default, local data is stored in `.jupiter-wallet-bot/` in the project directory. This directory is ignored by Git. Set `JWB_DATA_DIR` to use another location.

- `wallets.sqlite3`: metadata, queue, and encrypted credential records
- `browser-profile/`: dedicated Chromium profile (contains session data; keep private)
- `backups/`: encrypted database backup files
- `vault.json`: Argon2id salt and encrypted verifier; required with the master password to unlock backups

## Tests

```powershell
pytest
```

## Current scope

This repository provides the secure application foundation, queue lifecycle, browser launcher, human checkpoints, encrypted vault, CLI, and tests. Extension-specific screen recognition and navigation should only be added after inspecting the real onboarding UI and validating the extension package. Never automate or store a recovery phrase without explicit user authorization.
