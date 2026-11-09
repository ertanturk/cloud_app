# Implementation Roadmap

---

## Phase 1: Core Configuration & Database Setup

### 1.1 Environment & Settings

- [x] **`cloud_backend/src/cloud_backend/core/config.py`**
    - Read `.env` variables using `pydantic-settings`.
    - Define `STORAGE_BASE_PATH`, `JWT_SECRET_KEY`, `CORE_DB_URL`, and `TELEMETRY_DB_URL`.
- [x] **`cloud_backend/src/cloud_backend/core/app_logging.py`**
    - Setup log format for standard output and application errors.
- [x] **`cloud_backend/src/cloud_backend/core/security.py`**
    - Build Argon2id hash & verify helper (Version 1 parameters).
    - Build AES encryption/decryption helpers for TOTP secrets.
    - Build JWT creation and validation functions (HS256, 10-min expiration).

### 1.2 Database Connection & Models

- [x] **`cloud_backend/src/cloud_backend/db/connection.py`**
    - Setup SQLAlchemy engine pools for Core DB and Telemetry DB.
- [x] **`cloud_backend/src/cloud_backend/db/models/core.py`**
    - Create `Users` table model.
    - Create `UserSecrets` table model.
    - Create `Sessions` table model.
    - Create `RefreshTokens` table model.
    - Create `Files` table model.
    - Create `UploadReservations` table model.
- [x] **`cloud_backend/src/cloud_backend/db/models/telemetry.py`**
    - Create `TelemetryEvents` table model.
    - Create `Telemetry` table model (nullable user_id, session_id).

---

## Phase 2: Database Repositories (Data Layer)

- [x] **`cloud_backend/src/cloud_backend/db/repositories/user_repo.py`**
    - Find user by username or user ID.
    - Lock user row (`UPDLOCK`, `HOLDLOCK`) for quota update.
    - Create user and update user quota.
- [x] **`cloud_backend/src/cloud_backend/db/repositories/session_repo.py`**
    - Create active session.
    - Update `last_activity_at`.
    - End active session (`ended_at`).
    - List active sessions for admin.
- [x] **`cloud_backend/src/cloud_backend/db/repositories/refresh_token_repo.py`**
    - Create refresh token record in `dbo.RefreshTokens`.
    - Rotate refresh token.
    - Revoke refresh token.
- [x] **`cloud_backend/src/cloud_backend/db/repositories/file_repo.py`**
    - Generate next ID from sequence `dbo.FileIdSequence`.
    - Create file record in `dbo.Files`.
    - List user active files.
    - Update file status to `deleting` and delete record.
- [x] **`cloud_backend/src/cloud_backend/db/repositories/reservation_repo.py`**
    - Create reservation row (`reserved`).
    - Update state (`uploading`, `completed`).
    - Find active reservations to calculate reserved quota.
- [x] **`cloud_backend/src/cloud_backend/db/repositories/telemetry_repo.py`**
    - Insert new telemetry event.
    - Query telemetry events with pagination and filters.

---

## Phase 3: Pydantic Schemas (Request / Response DTOs)

- [x] **`cloud_backend/src/cloud_backend/schemas/common.py`**
    - `ErrorResponse` schema (`code`, `message`).
    - `PaginationParams` schema (`limit`, `offset`).
- [x] **`cloud_backend/src/cloud_backend/schemas/auth.py`**
    - `LoginRequest` (`username`, `password`, `totp_code`).
    - `LoginResponse` (`access_token`, `refresh_token`, `expires_in`, `user`).
    - `TotpSetupResponse` (`provisioning_uri`, `setup_token`).
    - `TotpConfirmRequest` (`setup_token`, `totp_code`).
    - `RefreshRequest` (`refresh_token`).
- [x] **`cloud_backend/src/cloud_backend/schemas/file.py`**
    - `FileItemResponse` (`file_id`, `file_name`, `file_size_bytes`, `extension`, `uploaded_at`).
    - `StorageResponse` (`quota_bytes`, `used_bytes`, `reserved_bytes`, `available_bytes`).
- [x] **`cloud_backend/src/cloud_backend/schemas/upload.py`**
    - `UploadReservationRequest` (`file_name`, `file_size_bytes`).
    - `UploadReservationResponse` (`reservation_id`, `expires_at`).
- [x] **`cloud_backend/src/cloud_backend/schemas/admin.py`**
    - `UserCreateRequest` (`username`, `initial_password`).
    - `UserResponse` (`user_id`, `username`, `role`, `storage_quota_bytes`, `created_at`).
    - `QuotaUpdateRequest` (`quota_bytes`).
    - `SessionResponse` (`session_id`, `user_id`, `username`, `client_ip`, `started_at`, `last_activity_at`).
    - `TelemetryResponse` (`event_id`, `event_type`, `user_id`, `session_id`, `client_ip`, `telemetry_data`, `event_time`).
    - `SystemMetricsResponse` (CPU, RAM, Disk, Network speeds).
    - `ApplicationMetricsResponse` (Active sessions, active uploads, total users, total files, total storage).

---

## Phase 4: Backend Business Logic Services

- [x] **`cloud_backend/src/cloud_backend/services/auth_service.py`**
    - Validate password & TOTP code.
    - Rotate refresh token in single database transaction.
    - Detect token reuse (close session & revoke all tokens).
- [x] **`cloud_backend/src/cloud_backend/services/storage_service.py`**
    - Verify storage root directory safety (prevent path traversal).
    - Generate physical path: `{user_id}/{file_id}.{ext}`.
- [x] **`cloud_backend/src/cloud_backend/services/upload_service.py`**
    - Check available user quota.
    - Stream binary upload to `.tmp/{reservation_id}.part`.
    - Verify actual size & calculate SHA-256 checksum during streaming.
    - Move temp file to storage root and complete reservation.
- [x] **`cloud_backend/src/cloud_backend/services/file_service.py`**
    - List files logic.
    - Download file streaming logic.
    - Delete file logic (change state to `deleting`, remove disk file, remove DB row).
- [x] **`cloud_backend/src/cloud_backend/services/metrics_service.py`**
    - Read live CPU, RAM, Disk, Network speeds using `psutil`.
    - Calculate live application metrics from database.

---

## Phase 5: Backend API Routers & Main Application

- [x] **`cloud_backend/src/cloud_backend/api/v1/dependencies.py`**
    - Implement dependency injection
- [x] **`cloud_backend/src/cloud_backend/api/v1/auth.py`**
    - Implement endpoints: `/login`, `/totp/setup`, `/totp/confirm`, `/refresh`, `/logout`, `/heartbeat`.
- [x] **`cloud_backend/src/cloud_backend/api/v1/files.py`**
    - Implement endpoints: `GET /files`, `GET /files/{id}/download`, `DELETE /files/{id}`.
- [x] **`cloud_backend/src/cloud_backend/api/v1/uploads.py`**
    - Implement endpoints: `POST /uploads`, `PUT /uploads/{id}/content`, `DELETE /uploads/{id}`.
- [x] **`cloud_backend/src/cloud_backend/api/v1/storage.py`**
    - Implement endpoint: `GET /storage`.
- [x] **`cloud_backend/src/cloud_backend/api/v1/admin.py`**
    - Implement endpoints: `GET/POST /admin/users`, `PATCH /admin/users/{id}/quota`, `GET /admin/sessions`, `GET /admin/telemetry`, `GET /admin/metrics/*`.
- [x] **`cloud_backend/src/cloud_backend/api/v1/sse.py`**
    - Implement persistent Server-Sent Events endpoint (`GET /admin/events`) pushing system metrics every 2s.
- [x] **`cloud_backend/src/cloud_backend/api/router.py`**
    - Combine all v1 sub-routers into single master router.
- [x] **`cloud_backend/src/cloud_backend/main.py`**
    - Initialize FastAPI app, middleware, routes, and background task runners.

---

## Phase 6: Background Tasks

- [x] **`cloud_backend/src/cloud_backend/tasks/cleanup.py`**
    - Mark sessions inactive for >20 mins as ended.
- [x] **`cloud_backend/src/cloud_backend/tasks/garbage_collector.py`**
    - Clean orphaned `.tmp/upload_{file_id}.tmp` files.
    - Delete completed reservations older than 24 hours.
- [x] **`cloud_backend/src/cloud_backend/tasks/file_recovery.py`**
    - Retry physical or metadata deletion for files stuck in `deleting` status.
- [x] **`cloud_backend/src/cloud_backend/tasks/checksum_checker.py`**
    - Run weekly SHA-256 checksum check on all stored physical files.

---

## Phase 7: Frontend Services & Keyring

- [ ] **`cloud_frontend/src/cloud_frontend/services/auth_manager.py`**
    - Store JWT Access Token in application memory only.
- [ ] **`cloud_frontend/src/cloud_frontend/services/keyring_store.py`**
    - Save and load 30-day Refresh Token from OS Keyring.
- [ ] **`cloud_frontend/src/cloud_frontend/services/api_client.py`**
    - Build HTTP client with `httpx` to send requests and stream files.
- [ ] **`cloud_frontend/src/cloud_frontend/services/sse_client.py`**
    - Build SSE client with `httpx-sse` for admin live metrics updates.

---

## Phase 8: Frontend TUI (CLI & UI)

### 8.1 CLI Arguments & Themes

- [ ] **`cloud_frontend/src/cloud_frontend/cli/args.py`**
    - Parse CLI flags (`--admin`).
- [ ] **`cloud_frontend/src/cloud_frontend/ui/styles/theme.py`**
    - Define **Autumn Dark** color variables (`#292522`, Surface, Raised, Text, Status colors).

### 8.2 Custom Widgets

- [ ] **`cloud_frontend/src/cloud_frontend/ui/widgets/header.py`**
    - Display title `Cloud Store`, connection state, and username.
- [ ] **`cloud_frontend/src/cloud_frontend/ui/widgets/storage_bar.py`**
    - Render progress bar for used, reserved, and available quota.
- [ ] **`cloud_frontend/src/cloud_frontend/ui/widgets/file_table.py`**
    - Render interactive table of user files.
- [ ] **`cloud_frontend/src/cloud_frontend/ui/widgets/metrics_card.py`**
    - Render system metrics (CPU, RAM, Disk, Net) card widgets for admin.

### 8.3 Screens

- [ ] **`cloud_frontend/src/cloud_frontend/ui/screens/login.py`**
    - Form screen for username, password, and TOTP code.
- [ ] **`cloud_frontend/src/cloud_frontend/ui/screens/user_dashboard.py`**
    - Main User TUI screen (`U` upload, `D` download, `R` remove, `Q` quit).
- [ ] **`cloud_frontend/src/cloud_frontend/ui/screens/admin_dashboard.py`**
    - Main Admin dashboard with live metric cards and recent telemetry log.
- [ ] **`cloud_frontend/src/cloud_frontend/ui/screens/admin_sessions.py`**
    - Table screen displaying active user sessions.
- [ ] **`cloud_frontend/src/cloud_frontend/ui/screens/admin_telemetry.py`**
    - Table screen with filter inputs for event history.
- [ ] **`cloud_frontend/src/cloud_frontend/ui/screens/admin_users.py`**
    - User list screen and quota modification dialog.
- [ ] **`cloud_frontend/src/cloud_frontend/ui/screens/admin_register.py`**
    - Screen to add user and display terminal QR code for 2FA.

### 8.4 Frontend Entry Point

- [ ] **`cloud_frontend/src/cloud_frontend/main.py`**
    - Entry point for `uv run cloud` and `uv run cloud --admin`.

---

## Phase 9: Tests

- [ ] **`cloud_backend/tests/`**
    - Unit tests for security (Argon2id, JWT, TOTP).
    - Integration tests for upload reservation and quota calculations.
- [ ] **`cloud_frontend/tests/`**
    - Tests for keyring store and API client helpers.
