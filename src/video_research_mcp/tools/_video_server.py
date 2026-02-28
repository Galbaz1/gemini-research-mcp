"""Shared FastMCP sub-server instance for video tools.

Both video.py and video_session.py register tools on this shared instance,
avoiding circular imports while keeping a single server for mounting.
"""

from fastmcp import FastMCP

video_server = FastMCP("video")
