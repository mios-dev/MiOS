# AI-hint: Compatibility import for the canonical MCP federation router and SDK transports.
# AI-doc: usr/share/doc/mios/manual/federation.md
"""Keep the historical import path bound to the canonical MCP implementation.

The server imports mios_mcp directly. Exposing the same module here prevents a
second JSON-RPC transport and registry from drifting away from that live path.
"""
from __future__ import annotations

import sys
import mios_mcp as _canonical

sys.modules[__name__] = _canonical
