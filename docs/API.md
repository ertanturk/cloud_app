# API Design

## 1. Overview

CloudVault uses a TUI, an API Server, Microsoft SQL Server, and file-system storage.

The TUI communicates with the API Server. It must not connect directly to SQL Server or access server storage.

The application uses two databases:

- **Core Database:** users, secrets, sessions, refresh tokens, files, and upload reservations.
- **Telemetry Database:** application events, including events from unknown or unauthenticated users.

### General Rules

- API base path: `/api/v1`
- Normal request and response format: JSON
- File upload and download format: binary streams
- Authentication: JWT Bearer access token
- All timestamps use UTC.
- All file sizes use bytes.
- Use HTTPS outside local development.
- The server checks authentication, permissions, ownership, quota, and file operations.

## 2. Authentication

All authentication endpoints use the `/api/v1/auth` path.

### 2.1 Login

`POST /api/v1/auth/login`

Authentication: Not required.

Request:

```json
{
    "username": "ertan",
    "password": "user_password",
    "totp_code": "123456"
}
```

The server:

1. Finds the user by username.
2. Verifies the password with the user's Argon2id settings.
3. Checks that TOTP enrollment is complete.
4. Verifies the TOTP code.
5. Creates a session.
6. Creates an access token and a refresh token.

The response contains:

- `access_token`
- `refresh_token`
- `token_type` (`Bearer`)
- `expires_in` (600 seconds)
- `user` (`user_id`, `username`, and `role`)

The server must return a generic authentication error. It must not reveal whether the username, password, or TOTP code was incorrect.

Login attempts must be rate-limited.

### 2.2 TOTP Setup

`POST /api/v1/auth/totp/setup`

Authentication: Not required.

The user sends their username and initial password. The server verifies the credentials and starts TOTP enrollment.

The server creates a TOTP secret and returns a provisioning URI. The TUI displays a QR code from this URI.

The setup flow must use a short-lived setup token. The setup token is not an access token and cannot access normal API endpoints.

The `UserSecrets` model stores pending and confirmed TOTP secrets separately and
tracks enrollment with `totp_enabled`.

### 2.3 TOTP Confirmation

`POST /api/v1/auth/totp/confirm`

Authentication: Setup token.

The user sends the setup token and the first valid TOTP code.

The server verifies the code and marks TOTP enrollment as complete. The user cannot log in before enrollment is complete.

The database must support the enrollment state and the pending secret lifecycle.

### 2.4 Refresh Token

`POST /api/v1/auth/refresh`

Authentication: Not required. The refresh token is sent in the JSON body.

Request:

```json
{
    "raw_refresh_token": "current_refresh_token"
}
```

The server:

1. Calculates the SHA-256 hash of the supplied token.
2. Finds and locks the matching refresh-token row.
3. Checks token status, expiry, and session status.
4. Marks the old token as used.
5. Creates a new access token and refresh token.
6. Stores the new refresh-token hash.
7. Links the old token to the new token.
8. Commits all database changes in one Core Database transaction.

The response contains a new access token, refresh token, `token_type`, and `expires_in`.

A refresh token can be used only once. Reuse of a used token ends the related session and revokes all active refresh tokens for that session.

The TUI must allow only one refresh operation at a time.

### 2.5 Logout

`POST /api/v1/auth/logout`

Authentication: Not required. The refresh token is sent in the JSON body.

Request:

```json
{
    "raw_refresh_token": "current_refresh_token"
}
```

The server identifies the session from the refresh-token hash, sets `Sessions.ended_at`, and revokes all active refresh tokens for that session.

Logout is idempotent.

The TUI keeps quit and logout separate. `Q` exits without clearing the refresh
token, allowing automatic restore on the next start. `L` calls logout, clears the
access token from memory and the refresh token from the OS keyring, then exits.

If the server is unavailable, the TUI still clears local tokens and exits. The server's inactivity cleanup later ends the session.

### 2.6 Heartbeat

`POST /api/v1/auth/heartbeat`

Authentication: Required.

The server checks the access token and active session, then updates `Sessions.last_activity_at`.

The TUI sends a heartbeat at most once per minute while the user is actively interacting.

Background requests and token refresh do not count as user activity. Normal authenticated user actions update `last_activity_at` too.

### Session Rules

- Inactivity timeout: 20 minutes.
- A cleanup task checks inactive sessions every minute.
- Every authenticated request checks that the session is active and has not passed the inactivity timeout.
- An expired session cannot use the API even if its access token has not expired.
- Session timestamps are stored in UTC.

## 3. User API

All user endpoints require an access token.

The server gets the user ID from the token. The TUI must not send a user ID to choose which user's files it can access.

### 3.1 List Files

`GET /api/v1/files`

Returns the authenticated user's active files.

Query parameters:

| Parameter | Default |          Maximum |
| --------- | ------: | ---------------: |
| `limit`   |      50 |              100 |
| `offset`  |       0 | No fixed maximum |

Files are sorted by upload date, newest first.

Each file contains:

- `file_id`
- `file_name`
- `file_size_bytes`
- `extension`
- `uploaded_at`

The `Files` model stores `uploaded_at` and `status`, allowing the API to sort files
and exclude files being deleted.

### 3.2 Download File

`GET /api/v1/files/{file_id}/download`

Returns the file as a binary stream.

Response headers:

- `Content-Type: application/octet-stream`
- `Content-Disposition`: original file name
- `Content-Length`: file size
- `X-Content-SHA256`: expected file checksum

The server:

1. Finds the file by `file_id` and the authenticated `user_id`.
2. Checks that the file is active.
3. Reads the relative storage path from the Core Database.
4. Resolves the path under the configured storage root.
5. Checks that the resolved path stays inside the storage root.
6. Streams the file to the TUI.

The server must not accept a storage path from the client or expose the physical storage path.

The TUI writes the download to a temporary local `.part` file, verifies the
received byte count against `Content-Length`, and moves it to the final local
destination only after the file has been created successfully. The destination
may be an existing directory or an explicit file path.

Resumable downloads are not supported in v1. A failed download must start again.

If the database record exists but the physical file is missing, the server logs a storage error and returns a server-side storage error.

### 3.3 Create Upload Reservation

`POST /api/v1/uploads`

Authentication: Required.

Request:

```json
{
    "file_name": "document.pdf",
    "file_size_bytes": 2500000
}
```

The server:

1. Gets the user and session IDs from the access token.
2. Checks the file name and expected size.
3. Locks the user's row in the Core Database.
4. Calculates used bytes and reserved bytes.
5. Checks that the complete expected file size fits in the remaining quota.
6. Gets a new `file_id` from `dbo.FileIdSequence`.
7. Creates an upload reservation.
8. Commits the reservation before accepting file content.

The response contains:

- `reservation_id`
- `expires_at`

The complete file size must fit in the available quota before upload starts. A file cannot exceed the available quota by relying on a slow or streamed upload.

### 3.4 Upload File Content

`PUT /api/v1/uploads/{reservation_id}/content`

Authentication: Required.

The request body is the binary file content. It is not JSON.

There is one content upload request per file. Resumable and multi-request chunk uploads are not supported in v1.

The server:

1. Checks reservation ownership and state.
2. Changes the reservation state to `uploading`.
3. Streams the request body to a temporary file under `.tmp/`.
4. Counts the actual bytes and calculates SHA-256 while streaming.
5. Stops the upload if the actual size is greater than the reserved size.
6. Checks that the actual size equals the reserved size.
7. Moves the temporary file to its final storage path on the same file system.
8. Starts one Core Database transaction.
9. Inserts the file metadata into `dbo.Files`.
10. Changes the reservation to `completed` and records the resulting `file_id`.
11. Commits the transaction.
12. Reports success.

The file record and completed reservation must be committed in the same transaction.

The server must not create a file record for an incomplete upload.

### Upload Rules

- The server streams content and does not load the whole file into RAM.
- There is no fixed total upload duration.
- If no data arrives for 10 minutes, the server stops the upload.
- A failed upload returns the reservation to `reserved` after temporary or orphaned file cleanup succeeds.
- The user can retry with the same reservation.
- A reservation that has not started expires one hour after creation.
- A completed reservation is kept for 24 hours.
- Retrying a completed reservation returns the previous successful result. It must not create a duplicate file.
- A reservation continues to count against quota while it is `reserved` or `uploading`.
- A completed reservation does not count against quota.
- The server must check that enough physical disk space is available. User quota does not guarantee physical disk capacity.

**Database dependency:** The current `UploadReservations` table has no state or completion time. Add the fields needed to represent `reserved`, `uploading`, and `completed`, and to retain completed results for 24 hours. The existing `file_id` can identify the planned file ID and the completed file.

### 3.5 Cancel Upload

`DELETE /api/v1/uploads/{reservation_id}`

Authentication: Required.

The server checks reservation ownership.

- `reserved`: Delete the reservation and release its quota.
- `uploading`: Stop the upload, remove its temporary file, then delete the reservation.
- `completed`: Do not cancel or delete the file. The user must use the file deletion endpoint.

If physical file cleanup fails, the reservation must remain and continue to count against quota.

The server must prevent cancellation and upload completion from changing the same reservation at the same time.

### 3.6 Delete File

`DELETE /api/v1/files/{file_id}`

Authentication: Required.

The server:

1. Finds the file by `file_id` and the authenticated `user_id`.
2. Changes the file status from `active` to `deleting`.
3. Prevents new downloads of the file.
4. Deletes the physical file.
5. Deletes the file metadata row from the Core Database.

If physical deletion fails, the database row stays and the file returns to `active`.

If physical deletion succeeds but the database delete fails, the row stays in `deleting`. A recovery task retries the database delete.

Used quota goes down only after the metadata row is deleted.

**Database dependency:** Add a file status field that supports at least `active` and `deleting`.

### 3.7 Storage Information

`GET /api/v1/storage`

Authentication: Required.

Returns:

- `quota_bytes`
- `used_bytes`
- `reserved_bytes`
- `available_bytes`

Calculation:

`available_bytes = quota_bytes - used_bytes - reserved_bytes`

Rules:

- `quota_bytes` comes from `Users.storage_quota_bytes`.
- `used_bytes` is the sum of file sizes for records that still count toward quota, including files in `deleting` state.
- `reserved_bytes` is the sum of reservations in `reserved` or `uploading` state.
- Completed reservations do not count toward quota.
- The server calculates these values from the Core Database. It does not store a separate usage counter.

## 4. Admin API

All admin endpoints require an access token with the `admin` role.

### 4.1 List Users

`GET /api/v1/admin/users`

Returns users for the admin user-management screen.

Each user contains:

- `user_id`
- `username`
- `role`
- `storage_quota_bytes`
- `created_at`

The `Users` model stores `created_at`, which is returned to the admin UI.

### 4.2 Create User

`POST /api/v1/admin/users`

The admin provides:

- `username`
- `initial_password`

The server:

1. Checks that the username is unique.
2. Generates a unique random password salt.
3. Hashes the password with the configured Argon2id version.
4. Creates the user with the default quota and `user` role.
5. Creates the related `UserSecrets` row.
6. Starts the TOTP enrollment process.

Public registration is not supported.

The initial password must never be stored as plain text.

### 4.3 Change User Quota

`PUT /api/v1/admin/users/{user_id}/quota`

Request:

```json
{
    "quota_bytes": 20000000000
}
```

The server locks the user's row and calculates used bytes and reserved bytes.

The new quota must not be lower than used bytes plus reserved bytes.

The quota change takes effect after the Core Database transaction commits.

Only an admin can change a user's quota. A user cannot change their own quota.

### 4.4 Delete User

`DELETE /api/v1/admin/users/{user_id}`

Deletes an unused standard user. The operation is blocked when the user still has
files or session history.

### 4.5 Force Delete User

`DELETE /api/v1/admin/users/{user_id}/force`

Deletes a standard user, owned file metadata, upload reservations, sessions, refresh
tokens, and safely-owned physical files. Admin accounts and the current admin cannot
be deleted.

### 4.6 List Active Sessions

`GET /api/v1/admin/sessions`

Returns active sessions only.

Each session contains:

- `session_id`
- `user_id`
- `username`
- `client_ip`
- `started_at`
- `last_activity_at`

A session is active only when `ended_at` is `NULL` and its inactivity timeout has not expired.

The server must not show an expired session just because the cleanup task has not updated it yet.

The `Sessions` model stores `client_ip` for active-session administration.

### 4.7 Get Telemetry

`GET /api/v1/admin/telemetry`

Returns historical events from the Telemetry Database.

Query parameters:

| Parameter | Default |          Maximum |
| --------- | ------: | ---------------: |
| `limit`   |      50 |              100 |
| `offset`  |       0 | No fixed maximum |

Events are sorted newest first.

Each event contains:

- `event_id`
- `event_type`
- `user_id`, when known
- `session_id`, when known
- `client_ip`
- `telemetry_data`
- `event_time`

Telemetry includes successful and failed operations.

Event types include:

- Login success and failure
- Logout
- Upload started, completed, and failed
- Download completed and failed
- File deletion
- Session creation and expiration
- Server errors
- Storage errors

The Telemetry Database keeps logical user and session IDs without foreign keys to the Core Database. This allows events from unknown or unauthenticated users.

Telemetry must never store passwords, access tokens, refresh tokens, TOTP codes, or other secrets.

### 4.8 System Metrics

`GET /api/v1/admin/metrics/system`

Returns the current system metrics snapshot.

Metrics include:

- CPU usage percentage
- RAM used bytes, total bytes, and usage percentage
- Disk used bytes, total bytes, and usage percentage
- Network received bytes per second
- Network sent bytes per second

System metrics are collected every 2 seconds only while the admin dashboard is connected to the live events endpoint.

System metric samples are kept in memory and are not stored as historical rows in SQL Server.

### 4.9 Application Metrics

`GET /api/v1/admin/metrics/application`

Returns the current application metrics snapshot.

Metrics include:

- Active sessions
- Active uploads
- Total registered users
- Total stored files
- Total storage used

Active sessions and uploads are tracked by the application and updated when their state changes.

Other values are calculated when requested. Application metrics do not need a separate background collection job.

## 5. Live Admin Updates

`GET /api/v1/admin/events`

Authentication: Required. The user must have the `admin` role.

This endpoint uses Server-Sent Events (SSE). It sends server updates to the admin TUI through one persistent HTTP connection.

### Event Types

| Event                 | Data                               |
| --------------------- | ---------------------------------- |
| `system_metrics`      | System metrics snapshot            |
| `application_metrics` | Application metrics snapshot       |
| `session`             | Session created, updated, or ended |
| `telemetry`           | New telemetry event                |

### Connection Rules

1. The admin opens the dashboard.
2. The TUI requests the initial active sessions, telemetry, and application metrics.
3. The TUI opens the SSE connection.
4. The server starts system metric collection.
5. The server sends system metrics every 2 seconds.
6. The server sends session, application metric, and telemetry events when they change.
7. When the admin exits, the TUI closes the SSE connection.
8. The server stops system metric collection when the connection closes.

Only one admin account and one admin TUI connection are supported in v1.

If the SSE connection is lost, the TUI shows a disconnected status. The admin reconnects manually. When it reconnects, the TUI requests fresh snapshots.

SSE is only for server-to-client updates. Normal HTTP requests are used for admin actions.

## 6. Common API Rules

### 6.1 Authentication Header

Protected requests use:

`Authorization: Bearer <access_token>`

The server checks the token signature, issuer, audience, expiration, active session, and role when required.

### 6.2 Ownership

The server gets the user ID from the access token.

If a file or reservation does not exist or belongs to another user, the server returns the same not-found response.

This prevents users from discovering other users' resources.

### 6.3 Error Format

JSON errors use this format:

```json
{
    "error": {
        "code": "RESOURCE_NOT_FOUND",
        "message": "The requested resource was not found."
    }
}
```

### 6.4 HTTP Status Codes

| Status | Meaning                                  |
| ------ | ---------------------------------------- |
| 200    | Request completed                        |
| 201    | Resource created                         |
| 204    | Request completed with no response body  |
| 400    | Invalid request                          |
| 401    | Authentication failed or session expired |
| 403    | Permission denied                        |
| 404    | Resource not found                       |
| 409    | Resource state conflict                  |
| 413    | Request content is too large             |
| 429    | Too many requests                        |
| 500    | Internal server error                    |
| 503    | Service unavailable                      |

The server must not expose internal file paths, SQL errors, passwords, tokens, or secret values in error responses.

### 6.5 Activity and Session Checks

Every protected endpoint checks the active session and inactivity timeout.

Successful user actions update `last_activity_at`. Heartbeats also update it. Token refresh and background monitoring requests do not count as user activity.

Admin monitoring requests must not keep a normal user session alive by themselves.

## 7. File Storage and Recovery

SQL Server and the file system do not share one atomic transaction. The application must handle failures between file-system operations and database commits.

### 7.1 Upload Recovery

If the server crashes after moving a file to its final path but before the Core Database transaction commits:

- The file record is not created.
- The reservation remains in the database.
- Recovery checks the reservation and final file.
- The orphaned final file is removed.
- The reservation returns to `reserved`.
- The user can retry with the same reservation.

If the database transaction commits but the HTTP response is lost:

- The file record exists.
- The reservation is `completed`.
- The reservation stores the resulting `file_id`.
- Retrying the same reservation returns the existing result.

### 7.2 Garbage Collector

The garbage collector compares files on disk with file records and upload reservations.

It must:

- Remove temporary files left by failed uploads.
- Find final files without a matching `Files.storage_path` record.
- Ignore files belonging to active uploads.
- Delete orphaned final files only after a 24-hour safety period.
- Keep a reservation when file cleanup fails.
- Never delete an entire user directory because one file is missing.
- Log database records whose physical files are missing. It must not delete those records automatically.

The collector must not race with an active upload or a file deletion. It must check reservation and file states before removing a file.

### 7.3 File Deletion Recovery

Files in `deleting` state are checked by a recovery task.

- If the physical file still exists, retry physical deletion.
- If the physical file is already gone, retry deleting the database record.
- Keep the file record and its quota charge until the database record is deleted.

## 8. Security Rules

- Never store plain-text passwords.
- Use Argon2id for password hashing.
- Encrypt TOTP secrets in the Core Database.
- Use HS256 for access JWTs.
- Keep the JWT signing key outside the database. It must contain at least 256 bits.
- Generate 256-bit cryptographically random refresh tokens.
- Store only SHA-256 hashes of refresh tokens in SQL Server.
- Store raw refresh tokens in the TUI operating system keyring.
- Keep access tokens in TUI memory only.
- Check the active session on every protected request.
- Check ownership on every file and reservation operation.
- Check the admin role on every admin endpoint.
- Never store authentication secrets in telemetry.

## 9. Version 1 Limits

The following features are not supported in v1:

- Public user registration
- Resumable uploads
- Resumable downloads
- Multiple content requests for one file
- Historical system metric storage
- WebSocket connections
- Browser-based administration
- Multiple admin accounts
- Multiple simultaneous admin TUI connections

## 10. Database Alignment

The Core and Telemetry database designs are aligned with the implemented API and
Alembic migrations.

### Core Database Changes

1. **Sessions**
    - `client_ip` is stored so the admin can see the client address.

2. **Files**
    - `uploaded_at` supports file-list sorting.
    - `status` supports `active` and `deleting`.

3. **UploadReservations**
    - `status` supports `reserved`, `uploading`, and `completed`.
    - Keep completed reservations for 24 hours.
    - Keep the planned `file_id` and use it to return the previous result after a lost HTTP response.
    - The time fields distinguish reservation expiry, upload activity, and completed-result retention.
    - Recoverable upload failures return to `reserved` after file cleanup succeeds.

4. **UserSecrets / TOTP enrollment**
    - `totp_enabled` identifies the enrollment state.
    - Pending secrets are stored separately and moved to the confirmed field after validation.
    - Setup tokens are stored as hashes with an expiry timestamp.

5. **Users**
    - `created_at` is returned by the admin user list.

### Telemetry Database

The current Telemetry Database already supports nullable logical user and session IDs, client IP, event type, JSON event data, and UTC event time. Keep it separate from the Core Database.

### Rules That Must Stay Consistent

- A file record is created only after the complete file has been received and stored.
- The file record and completed reservation are committed in one Core Database transaction.
- A completed reservation does not count toward quota.
- `reserved` and `uploading` reservations count toward quota.
- Files in `active` and `deleting` states count toward quota until their database records are deleted.
- Physical file cleanup must succeed before an upload reservation is released after a failed upload.
- Physical file deletion must succeed before a file record is deleted.
