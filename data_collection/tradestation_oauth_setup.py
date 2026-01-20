#!/usr/bin/env python3
"""
TradeStation OAuth Setup Helper

This script helps you obtain the initial refresh token for TradeStation API access.
Run this once to get your refresh token, then use tradestation_api_access.py for data collection.

Usage:
    1. Get your API credentials from TradeStation Developer Portal
    2. Run: poetry run python data_collection/tradestation_oauth_setup.py
    3. Follow the prompts
"""

import http.server
import socketserver
import webbrowser
import urllib.parse
import requests
import json
import os
import threading
import time

# OAuth endpoints
AUTH_URL = "https://signin.tradestation.com/authorize"
TOKEN_URL = "https://signin.tradestation.com/oauth/token"
AUDIENCE = "https://api.tradestation.com"

# Localhost callback configuration
# TradeStation allows these ports: 80, 3000, 3001, 8080, 31022
CALLBACK_PORT = 8080
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}"

# Store the authorization code when received
auth_code = None
server_should_stop = False


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """Handle the OAuth callback and extract the authorization code."""

    def do_GET(self):
        global auth_code, server_should_stop

        # Parse the query string
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if 'code' in params:
            auth_code = params['code'][0]

            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            success_html = """
            <html>
            <head><title>Authorization Successful</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: green;">✓ Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                <p>Your authorization code has been received.</p>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode())
            server_should_stop = True

        elif 'error' in params:
            error = params.get('error', ['Unknown'])[0]
            error_desc = params.get('error_description', ['No description'])[0]

            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            error_html = f"""
            <html>
            <head><title>Authorization Failed</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: red;">✗ Authorization Failed</h1>
                <p><strong>Error:</strong> {error}</p>
                <p><strong>Description:</strong> {error_desc}</p>
                <p>Please try again.</p>
            </body>
            </html>
            """
            self.wfile.write(error_html.encode())
            server_should_stop = True
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default logging
        pass


def build_auth_url(client_id):
    """Build the authorization URL with required parameters."""
    params = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': REDIRECT_URI,
        'audience': AUDIENCE,
        'scope': 'openid offline_access profile MarketData ReadAccount Trade OptionSpreads',
        'state': 'optionsmagic_setup'
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(client_id, client_secret, code):
    """Exchange the authorization code for access and refresh tokens."""
    data = {
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'redirect_uri': REDIRECT_URI
    }

    response = requests.post(
        TOKEN_URL,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data=data
    )

    if response.status_code == 200:
        return response.json()
    else:
        print(f"\nError exchanging code: {response.status_code}")
        print(f"Response: {response.text}")
        return None


def save_tokens(client_id, client_secret, refresh_token, filename='tokens.json'):
    """Save the tokens to a JSON file."""
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token
    }

    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"\n✓ Tokens saved to {filename}")


def main():
    global auth_code, server_should_stop

    print("=" * 60)
    print("TradeStation OAuth Setup")
    print("=" * 60)
    print()
    print("This script will help you obtain your initial refresh token.")
    print("You'll need your API credentials from the TradeStation Developer Portal.")
    print()
    print("Prerequisites:")
    print("  1. A TradeStation account (funded with $10,000+ for free API access)")
    print("  2. API credentials from: https://developer.tradestation.com/")
    print()

    # Get credentials from user
    client_id = input("Enter your Client ID (API Key): ").strip()
    if not client_id:
        print("Error: Client ID is required")
        return

    client_secret = input("Enter your Client Secret: ").strip()
    if not client_secret:
        print("Error: Client Secret is required")
        return

    print()
    print("-" * 60)
    print("Step 1: Starting local callback server...")
    print(f"        Listening on {REDIRECT_URI}")
    print("-" * 60)

    # Start local server in a thread
    handler = OAuthCallbackHandler

    try:
        with socketserver.TCPServer(("", CALLBACK_PORT), handler) as httpd:
            # Make the server non-blocking
            httpd.timeout = 1

            # Build and open auth URL
            auth_url = build_auth_url(client_id)

            print()
            print("-" * 60)
            print("Step 2: Opening browser for authorization...")
            print("-" * 60)
            print()
            print("If the browser doesn't open automatically, visit this URL:")
            print()
            print(auth_url)
            print()

            # Try to open browser
            webbrowser.open(auth_url)

            print("Waiting for authorization...")
            print("(Log in to TradeStation and authorize the application)")
            print()

            # Wait for callback with timeout
            timeout = 300  # 5 minutes
            start_time = time.time()

            while not server_should_stop and (time.time() - start_time) < timeout:
                httpd.handle_request()

            if not auth_code:
                print("\nTimeout or error waiting for authorization.")
                return

    except OSError as e:
        print(f"\nError starting server on port {CALLBACK_PORT}: {e}")
        print("Make sure the port is not in use by another application.")
        return

    print()
    print("-" * 60)
    print("Step 3: Exchanging authorization code for tokens...")
    print("-" * 60)

    tokens = exchange_code_for_tokens(client_id, client_secret, auth_code)

    if not tokens:
        print("\nFailed to exchange code for tokens.")
        return

    refresh_token = tokens.get('refresh_token')
    access_token = tokens.get('access_token')

    if not refresh_token:
        print("\nWarning: No refresh token received.")
        print("Make sure 'offline_access' scope is included.")
        return

    print()
    print("-" * 60)
    print("Step 4: Saving credentials...")
    print("-" * 60)

    # Save to tokens.json
    save_tokens(client_id, client_secret, refresh_token)

    # Also show env var format
    print()
    print("Alternatively, add these to your .env file:")
    print()
    print(f"TRADESTATION_CLIENT_ID={client_id}")
    print(f"TRADESTATION_CLIENT_SECRET={client_secret}")
    print(f"TRADESTATION_REFRESH_TOKEN={refresh_token}")

    print()
    print("=" * 60)
    print("✓ Setup Complete!")
    print("=" * 60)
    print()
    print("You can now run the options data collection script:")
    print("  poetry run python data_collection/tradestation_api_access.py")
    print()

    # Test the token
    print("Testing API access...")
    headers = {'Authorization': f'Bearer {access_token}'}
    test_response = requests.get(
        'https://api.tradestation.com/v3/marketdata/options/expirations/AAPL',
        headers=headers
    )

    if test_response.status_code == 200:
        data = test_response.json()
        exp_count = len(data.get('Expirations', []))
        print(f"✓ API access verified! Found {exp_count} AAPL option expirations.")
    elif test_response.status_code == 403:
        print(f"⚠ API test returned status 403 - Missing required scope")
        print()
        print("This usually means:")
        print("  1. The 'MarketData' scope wasn't granted during authorization")
        print("  2. Your TradeStation account doesn't have API market data access")
        print()
        print("Scopes granted in your token:")
        granted_scopes = tokens.get('scope', 'unknown')
        print(f"  {granted_scopes}")
        print()
        print("Required scopes for options data: MarketData")
        print()
        print("To fix this:")
        print("  1. Log into TradeStation Developer Portal")
        print("  2. Check your app has 'MarketData' scope enabled")
        print("  3. Re-run this setup script to re-authorize")
        print()
        print("If you have a sim account, try the sim API endpoint instead.")
    else:
        print(f"⚠ API test returned status {test_response.status_code}")
        print(f"  Response: {test_response.text[:200]}")


if __name__ == "__main__":
    main()
