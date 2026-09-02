"""Outbound integrations with external QA systems."""

from qa_mcp.integrations.xray import XrayClient, XrayError

__all__ = ["XrayClient", "XrayError"]
