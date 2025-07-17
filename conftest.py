import os
import sys
from cryptography.fernet import Fernet

# Set a dummy encryption key for the test environment.
# This must be done before other modules (like database.operations) are imported,
# as they may depend on this environment variable at import time.
# A valid Fernet key must be 32 url-safe base64-encoded bytes.
if "ENCRYPTION_KEY" not in os.environ:
    key = Fernet.generate_key()
    os.environ["ENCRYPTION_KEY"] = key.decode()

# Add the project root to the Python path to allow for absolute imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
