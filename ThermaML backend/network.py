import socket
import os
from urllib.parse import urlparse

base_url = os.getenv("FORTYGUARD_BASE_URL", "https://api.fortyguard.com")
hostname = urlparse(base_url).hostname

print(f"Target Hostname: {hostname}")

try:
    ip = socket.gethostbyname(hostname)
    print(f"DNS Resolution Successful: {hostname} -> {ip}")
except socket.gaierror as e:
    print(f"\n[DNS Resolution Failed]: {e}")
    print("Reasons:")
    print("1. FortyGuard has not yet opened/propagated their public API server for hackathon start.")
    print("2. The correct endpoint host may be specified in the Participant Handbook Quickstart notebook.")