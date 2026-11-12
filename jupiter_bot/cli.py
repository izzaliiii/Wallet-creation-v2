from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime, timezone

import typer
from rich.console import Console
from rich.table import Table

from .browser import BrowserManager
from .config import get_settings
from .database import Database
from .queue import QueueManager
from .vault import Vault
from .workflow import WalletWorkflow

app = typer.Typer(no_args_is_help=True, help="Personal Jupiter Wallet provisioning assistant.")
console = Console()


def services():
    settings = get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    db = Database(settings.database_path)
    db.initialize()
    return settings, db, QueueManager(db)


@app.command()
def start():
    """Initialize local storage and validate basic configuration."""
    settings, _, _ = services()
    console.print(f"[green]Database initialized:[/green] {settings.database_path}")
    console.print(f"Extension path configured: {bool(settings.extension_path)}")
    console.print(f"Extension ID: {settings.extension_id} (verify publisher and ID manually)")


@app.command()
def add(name: str = typer.Option(..., "--name", prompt=True), network: str = typer.Option("Solana", "--network")):
    """Add a wallet request to the sequential creation queue."""
    _, _, manager = services()
    request_id = manager.add(name, network)
    console.print(f"Queued [bold]{name}[/bold] with ID {request_id}")


@app.command()
def queue():
    """Display wallet creation requests."""
    _, _, manager = services()
    rows = manager.list()
    table = Table("ID", "Account", "Network", "Status", "Created")
    for row in rows:
        table.add_row(row["id"][:8], row["account_name"], row["network"], row["status"], row["created_at"][:19])
    console.print(table)


@app.command()
def process():
    """Process queued requests with mandatory human onboarding."""
    settings, db, manager = services()
    vault = Vault(settings.data_dir)
    vault.initialize_or_unlock()
    browser = BrowserManager(settings)
    try:
        WalletWorkflow(db, manager, vault, browser).process_queue()
    finally:
        browser.close()
        vault.lock()


@app.command("list")
def list_wallets():
    """List saved wallet metadata (never secrets)."""
    _, db, _ = services()
    with db.connect() as conn:
        rows = conn.execute("SELECT id, account_name, public_address, network, created_at, status FROM wallets ORDER BY created_at").fetchall()
    table = Table("ID", "Account", "Address", "Network", "Status")
    for row in rows:
        table.add_row(row["id"][:8], row["account_name"], row["public_address"], row["network"], row["status"])
    console.print(table)


@app.command()
def details(id: str = typer.Option(..., "--id")):
    """Show public wallet metadata."""
    _, db, _ = services()
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM wallets WHERE id LIKE ?", (f"{id}%",)).fetchone()
    if not row:
        raise typer.Exit(1)
    for key in ("id", "account_name", "public_address", "network", "created_at", "status"):
        console.print(f"{key}: {row[key]}")


@app.command()
def retrieve(id: str = typer.Option(..., "--id")):
    """Decrypt a stored secret after explicit confirmation."""
    settings, db, _ = services()
    vault = Vault(settings.data_dir)
    vault.initialize_or_unlock()
    try:
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT e.* FROM encrypted_credentials e JOIN wallets w ON w.id=e.wallet_id WHERE w.id LIKE ?",
                (f"{id}%",),
            ).fetchall()
        if not rows:
            console.print("No encrypted credentials found.")
            return
        if input("Displaying a recovery secret is risky. Type DISPLAY to proceed: ").strip() != "DISPLAY":
            return
        for row in rows:
            secret = vault.decrypt(row["ciphertext"], row["nonce"], row["wallet_id"], row["secret_type"])
            console.print(f"\\n{row['secret_type']} (keep private):")
            console.print(secret, markup=False)
    finally:
        vault.lock()


@app.command()
def verify(id: str = typer.Option(..., "--id")):
    """Open the extension so the user can manually verify wallet access."""
    settings, db, _ = services()
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM wallets WHERE id LIKE ?", (f"{id}%",)).fetchone()
    if not row:
        raise typer.BadParameter("Wallet ID not found.")
    browser = BrowserManager(settings)
    try:
        page = browser.open_onboarding()
        console.print(f"Extension opened at {page.url}")
        input(f"Verify {row['account_name']} / {row['public_address']} in the extension, then press Enter...")
    finally:
        browser.close()


@app.command()
def backup():
    """Create an AES-256-GCM encrypted SQLite backup."""
    settings, db, _ = services()
    vault = Vault(settings.data_dir)
    vault.initialize_or_unlock()
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = settings.backup_dir / f"wallets-{stamp}.jwbak"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix="jwb-", suffix=".sqlite3", dir=settings.backup_dir, delete=False) as temp:
            temporary = temp.name
        with db.connect() as source:
            destination = sqlite3.connect(temporary)
            source.backup(destination)
            destination.close()
        encrypted = vault.encrypt_backup(open(temporary, "rb").read())
        target.write_bytes(encrypted)
        try:
            target.chmod(0o600)
        except OSError:
            pass
        console.print(f"Encrypted backup created: {target}")
        console.print("Keep vault.json and the master password. Both are required to restore and decrypt this backup.")
    finally:
        if temporary:
            try:
                import os
                os.remove(temporary)
            except OSError:
                pass
        vault.lock()


@app.command()
def lock():
    """Vault keys are only held in process memory and are cleared when each command exits."""
    console.print("Vault is locked; no key is persisted between CLI commands.")
