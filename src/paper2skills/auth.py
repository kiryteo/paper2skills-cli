"""GitHub Copilot OAuth device flow authentication.

Handles:
1. Device flow login (browser-based, stores OAuth token locally)
2. Token discovery: stored token > VS Code config > env var
3. Token storage at ~/.config/paper2skills/copilot_token.json
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import requests
from rich.console import Console

console = Console(stderr=True)

# Copilot's official OAuth App client ID (same as VS Code Copilot extension)
COPILOT_CLIENT_ID = "Iv1.b507a08c87ecfe98"

# Where we store the token
TOKEN_DIR = Path.home() / ".config" / "paper2skills"
TOKEN_FILE = TOKEN_DIR / "copilot_token.json"

# VS Code Copilot config locations (for auto-detect)
_VSCODE_COPILOT_PATHS = [
    Path.home() / ".config" / "github-copilot" / "hosts.json",
    Path.home() / ".config" / "github-copilot" / "apps.json",
]

# macOS-specific paths
import platform

if platform.system() == "Darwin":
    _VSCODE_COPILOT_PATHS.extend(
        [
            Path.home()
            / "Library"
            / "Application Support"
            / "github-copilot"
            / "hosts.json",
            Path.home()
            / "Library"
            / "Application Support"
            / "github-copilot"
            / "apps.json",
        ]
    )


def get_copilot_oauth_token() -> Optional[str]:
    """Find a Copilot OAuth token from any available source.

    Search order:
    1. Stored token from 'paper2skills login'
    2. VS Code Copilot config files
    3. GITHUB_COPILOT_TOKEN env var (if set, assumed to be OAuth)

    Returns None if no token found anywhere.
    """
    import os

    # 1. Check our own stored token
    token = _read_stored_token()
    if token:
        return token

    # 2. Check VS Code Copilot config
    token = _read_vscode_token()
    if token:
        return token

    # 3. Check env var (user may have set this manually)
    token = os.environ.get("GITHUB_COPILOT_TOKEN", "")
    if token:
        return token

    return None


def _read_stored_token() -> Optional[str]:
    """Read token stored by 'paper2skills login'."""
    if not TOKEN_FILE.exists():
        return None

    try:
        data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        token = data.get("oauth_token", "")
        if token:
            return token
    except (json.JSONDecodeError, OSError):
        pass

    return None


def _read_vscode_token() -> Optional[str]:
    """Read OAuth token from VS Code's GitHub Copilot config."""
    for path in _VSCODE_COPILOT_PATHS:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # hosts.json format: {"github.com": {"user": "...", "oauth_token": "..."}}
            if "github.com" in data:
                token = data["github.com"].get("oauth_token", "")
                if token:
                    return token
            # apps.json format may differ — try top-level keys
            for key, val in data.items():
                if isinstance(val, dict) and "oauth_token" in val:
                    return val["oauth_token"]
        except (json.JSONDecodeError, OSError):
            continue

    return None


def _store_token(oauth_token: str, user: str = "") -> None:
    """Persist the OAuth token for future use."""
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(
        json.dumps(
            {
                "oauth_token": oauth_token,
                "user": user,
                "created_at": int(time.time()),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    # Restrict permissions (owner-only read/write)
    TOKEN_FILE.chmod(0o600)


def device_flow_login() -> str:
    """Run the GitHub device flow to get a Copilot OAuth token.

    Opens the user's browser to authorize, polls for the token.
    Stores the token at ~/.config/paper2skills/copilot_token.json.

    Returns the OAuth token string.
    """
    # Step 1: Request a device code
    console.print("[bold]Starting GitHub Copilot login...[/bold]\n")

    resp = requests.post(
        "https://github.com/login/device/code",
        json={
            "client_id": COPILOT_CLIENT_ID,
            "scope": "read:user",
        },
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "GitHubCopilotChat/0.35.0",
        },
        timeout=30,
    )
    resp.raise_for_status()
    device_data = resp.json()

    device_code = device_data["device_code"]
    user_code = device_data["user_code"]
    verification_uri = device_data["verification_uri"]
    interval = device_data.get("interval", 5)
    expires_in = device_data.get("expires_in", 900)

    # Step 2: Show the user code and open browser
    console.print(f"  1. Open: [cyan bold]{verification_uri}[/cyan bold]")
    console.print(f"  2. Enter code: [green bold]{user_code}[/green bold]")
    console.print(f"  3. Authorize the application\n")

    # Try to open browser automatically
    try:
        import webbrowser

        webbrowser.open(verification_uri)
        console.print("[dim]  (Browser opened automatically)[/dim]\n")
    except Exception:
        pass

    # Step 3: Poll for the token
    console.print("Waiting for authorization", end="")
    deadline = time.time() + expires_in

    while time.time() < deadline:
        time.sleep(interval)
        console.print(".", end="")

        resp = requests.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": COPILOT_CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "GitHubCopilotChat/0.35.0",
            },
            timeout=30,
        )
        resp.raise_for_status()
        token_data = resp.json()

        error = token_data.get("error")
        if error == "authorization_pending":
            continue
        elif error == "slow_down":
            interval = token_data.get("interval", interval + 5)
            continue
        elif error == "expired_token":
            console.print("\n[red]Device code expired. Please try again.[/red]")
            raise SystemExit(1)
        elif error == "access_denied":
            console.print(
                "\n[red]Authorization denied. "
                "Make sure your account has a Copilot subscription.[/red]"
            )
            raise SystemExit(1)
        elif error:
            console.print(f"\n[red]Unexpected error: {error}[/red]")
            raise SystemExit(1)

        # Success!
        oauth_token = token_data.get("access_token", "")
        if not oauth_token:
            console.print(f"\n[red]No access_token in response: {token_data}[/red]")
            raise SystemExit(1)

        console.print()  # newline after dots

        # Optionally get user info
        user = ""
        try:
            user_resp = requests.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {oauth_token}"},
                timeout=10,
            )
            if user_resp.ok:
                user = user_resp.json().get("login", "")
        except Exception:
            pass

        # Store the token
        _store_token(oauth_token, user)

        if user:
            console.print(f"\n[green bold]Logged in as {user}![/green bold]")
        else:
            console.print("\n[green bold]Login successful![/green bold]")

        console.print(f"  Token stored at: [dim]{TOKEN_FILE}[/dim]")

        return oauth_token

    console.print("\n[red]Timed out waiting for authorization.[/red]")
    raise SystemExit(1)


def logout() -> bool:
    """Remove stored Copilot token. Returns True if a token was removed."""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        return True
    return False
