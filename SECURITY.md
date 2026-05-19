# Security Policy for Xavani Agent

## Built by Enternovate — Open Source. Private. Local.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x | ✅ Active development — security patches within 7 days |
| < 0.1 | ❌ Pre-release versions not supported |

## Reporting a Vulnerability

Xavani Agent takes security seriously. We maintain a zero-telemetry,
zero-phone-home policy. If you discover a security vulnerability, please
report it privately.

**DO NOT** file a public GitHub issue for security vulnerabilities.

## Contact

- **Email**: security@enternovate.com
- **Response time**: < 48 hours for initial acknowledgment
- **Fix timeline**: Critical (CVSS 9-10) within 7 days of confirmation

## What We Secure

Xavani Agent runs entirely locally on your machine. Our security model
is built on these principles:

### 1. Zero Telemetry
Xavani collects NOTHING. No analytics, no crash reports, no usage data.
The `HERMES_DISABLE_TELEMETRY` and `DO_NOT_TRACK` environment variables
are forced at startup. Your data never leaves your machine.

### 2. Local-Only Architecture
- All data stored in `~/.xavani/` on your local machine
- No cloud dependency for core functionality
- MCP gateway runs on localhost:8080 (not exposed to network)
- API keys stored in local `~/.xavani/.env` file (never uploaded)

### 3. MCP Gateway Security
The OAG Proxy enforces these layers:
- **Authentication**: API keys or JWT tokens required for gateway access
- **Rate limiting**: Configurable per-user/per-tool (default 30 req/min)
- **Policy engine**: Allow/deny rules for specific tools and resources
- **Audit logging**: Every request logged to SQLite with full trace
- **Sandbox tiers**: Process isolation levels for untrusted servers

### 4. Skills Security
Each skill in the built-in registry is reviewed for:
- No hardcoded secrets or API keys in skill code
- No network calls that exfiltrate data
- No filesystem access outside designated skill directories
- Security scanning on install verifies command injection safety

### 5. API Key Safety
- API keys stored in `~/.xavani/.env` (never in code)
- `.env` file has 600 permissions (owner read/write only)
- Migration scripts explicitly strip API keys before copying config
- No API keys in logs, traces, or audit trails

### 6. Supply Chain Security
- Exact-pinned dependencies (no version ranges)
- `uv.lock` lockfile for reproducible installs
- Dependency scanning via OSV Scanner in CI
- All MCP servers scanned for injection risks before install

## Security Checklist for Users

- [ ] Store API keys only in `~/.xavani/.env`
- [ ] Set `.env` permissions: `chmod 600 ~/.xavani/.env`
- [ ] Review installed MCP servers before granting tool access
- [ ] Use rate limiting on public-facing gateway endpoints
- [ ] Enable audit logging for production use
- [ ] Keep Xavani updated: `pip install -U xavani-agent`

## Known Security Considerations

1. **MCP server trust**: Installed MCP servers have the same privileges as
   the Xavani process. Only install servers from trusted sources.
2. **Gateway exposure**: The MCP gateway binds to localhost by default.
   Do not expose port 8080 to untrusted networks without auth enabled.
3. **Plugin code**: Third-party plugins run in-process. Review plugin code
   before installing.

## Disclosure Policy

When a vulnerability is reported:
1. Acknowledgment within 48 hours
2. Investigation and fix development
3. Fix released as a patch version
4. Public disclosure after the fix is available
5. Credit to the reporter in release notes (if desired)

## Built by Enternovate

Xavani Agent is maintained by Enternovate. We believe open-source AI
infrastructure should be private, local, and secure by default.

Last updated: May 2026
