#!/usr/bin/env python3
"""
Request Hetzner Cloud console access
"""
import requests
import sys

HETZNER_TOKEN = "EDUqg20RTBb03W0wvtNMyD83PCzREabBmZOrVh7SX5622WQkdSrB2QdkG6LmTGS9"
SERVER_ID = "110615717"

headers = {
    "Authorization": f"Bearer {HETZNER_TOKEN}",
    "Content-Type": "application/json"
}

# Request console access
response = requests.post(
    f"https://api.hetzner.cloud/v1/servers/{SERVER_ID}/actions/request_console",
    headers=headers,
    json={"type": "vnc"}
)

if response.status_code == 201:
    data = response.json()
    print("✓ Console access granted!")
    print(f"URL: {data['action']['wss_url']}")
    print(f"Password: {data['action']['password']}")
    print(f"\nOpen this URL in your browser:")
    print(f"https://console.hetzner.cloud/?server_id={SERVER_ID}&websocket_url={data['action']['wss_url']}&password={data['action']['password']}")
else:
    print(f"✗ Failed: {response.status_code}")
    print(response.text)
