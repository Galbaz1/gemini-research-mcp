# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in video-research-mcp, please report it responsibly.

**Do not open a public issue.** Instead, email security concerns to the maintainer or use [GitHub's private vulnerability reporting](https://github.com/Galbaz1/video-research-mcp/security/advisories/new).

We will respond within 72 hours and work with you on a fix before public disclosure.

## Scope

This project is an MCP server that proxies requests to the Google Gemini API. Security-relevant areas include:

- **API key handling**: `GEMINI_API_KEY` is read from environment variables only, never logged or cached to disk
- **URL validation**: YouTube URLs are validated against actual youtube.com/youtu.be hosts to reject spoofed domains
- **File access**: `content_analyze` and `video_analyze` accept local file paths; access is limited to what the process user can read
- **Installer**: the npx installer writes files only to `~/.claude/` or `./.claude/` and `.mcp.json`

## Best Practices for Users

- Never commit your `GEMINI_API_KEY` to version control (`.env` is gitignored by default)
- Use `${GEMINI_API_KEY}` environment variable references in `.mcp.json` instead of hardcoded keys
- Review files before running `npx video-research-mcp@latest --force` (the `--force` flag overwrites your customizations)

## Supported Versions

Only the latest release is actively maintained.
