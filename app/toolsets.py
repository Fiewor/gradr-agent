import os
from pathlib import Path

import google.auth
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.genai import types
from mcp import StdioServerParameters

_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

# Check and set MongoDB MCP connection
mongodb_uri = os.environ.get("MDB_MCP_CONNECTION_STRING") or ""
if mongodb_uri:
    os.environ["MDB_MCP_CONNECTION_STRING"] = mongodb_uri
    os.environ["MONGODB_URI"] = mongodb_uri

# Resolve paths relative to project root (avoid hardcoded absolute paths)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_MCP_SERVER_PATH = str(_PROJECT_ROOT / "gradr_mcp" / "server.py")
_MCP_PYTHON_PATH = str(_PROJECT_ROOT / "gradr_mcp" / ".venv" / "bin" / "python")

from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.auth.transport.requests import Request
from google.oauth2 import id_token

# Connect to the remote Cloud Run MCP server securely via Streamable HTTP
_CLOUD_RUN_URL = "https://gradrmcp-943768265988.us-central1.run.app"

try:
    # Fetch an OIDC identity token to pass the Cloud Run IAM authentication
    token = id_token.fetch_id_token(Request(), _CLOUD_RUN_URL)
    headers = {"Authorization": f"Bearer {token}"}
except Exception as e:
    # Fallback (e.g. if local credentials don't support ID token fetching easily)
    headers = {}

custom_mcp_connection = StreamableHTTPConnectionParams(
    url=f"{_CLOUD_RUN_URL}/mcp",
    headers=headers,
    timeout=45.0
)
custom_mcp_toolset = McpToolset(connection_params=custom_mcp_connection)

# MongoDB MCP toolset configuration
# Only pass the connection string — do not leak other secrets to the subprocess
mongo_mcp_env = {
    "MDB_MCP_CONNECTION_STRING": os.environ.get("MDB_MCP_CONNECTION_STRING", ""),
    "PATH": os.environ.get("PATH", ""),
    "HOME": os.environ.get("HOME", ""),
    "NODE_PATH": os.environ.get("NODE_PATH", ""),
}
mongo_mcp_params = StdioServerParameters(
    command="npx", args=["-y", "mongodb-mcp-server"], env=mongo_mcp_env
)
mongo_mcp_connection = StdioConnectionParams(
    server_params=mongo_mcp_params, timeout=45.0
)
mongo_mcp_toolset = McpToolset(connection_params=mongo_mcp_connection)

# Google Cloud Storage MCP toolset configuration
gcs_mcp_params = StdioServerParameters(
    command="npx", args=["-y", "@google-cloud/storage-mcp"], env={**os.environ}
)
gcs_mcp_connection = StdioConnectionParams(server_params=gcs_mcp_params, timeout=45.0)
gcs_mcp_toolset = McpToolset(connection_params=gcs_mcp_connection)

retry_config = types.HttpRetryOptions(
    attempts=5, exp_base=2, initial_delay=2, http_status_codes=[429, 500, 503, 504]
)
