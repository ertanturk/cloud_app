# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1.0 | :x:                |

## Reporting a Vulnerability

We take the security of **Cloud Store** very seriously. If you believe you have found a security vulnerability in this project, please report it to us responsibly.

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please send an email to the project maintainers with details about the vulnerability. Include the following information in your report:

- Type of issue (e.g. SQL injection, JWT validation bypass, path traversal, TOTP setup flaw)
- Step-by-step instructions to reproduce the vulnerability
- Affected components (`cloud_backend` or `cloud_frontend`)
- Potential impact of the issue

### Vulnerability Response Timeline

- **Acknowledgement:** Within 48 hours of receiving your report.
- **Assessment:** Within 5 business days, confirming the issue and severity.
- **Fix Release:** We aim to release a patch as quickly as possible depending on severity.

## Core Security Architecture & Parameters

For reference, **Cloud Store** enforces the following security design rules:

1. **Password Hashing:** Uses **Argon2id** (Memory: 19456 KiB, Iterations: 2, Parallelism: 1, Salt: 16-byte random, Hash: 32-byte output). Plain-text passwords are never stored or logged.
2. **Two-Factor Authentication (TOTP):** Mandatory 6-digit TOTP confirmation. TOTP secrets are encrypted with AES before being stored in `UserSecrets`.
3. **Session & Access Tokens:** Short-lived 10-minute JWTs signed with **HS256** (256-bit secret key). Access tokens reside only in client TUI memory.
4. **Refresh Token Rotation:** 30-day opaque 32-byte refresh tokens stored in the OS Keyring. Server stores SHA-256 hashes only. Token reuse triggers immediate session termination and revocation.
5. **Path Traversal Protection:** User files are stored on disk as `{user_id}/{file_id}.{ext}`. User-supplied original file names are never used for disk storage paths.
