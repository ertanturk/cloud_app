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

## Phase 7: Windows Bootstrap & Backend Provisioning

This phase prepares a Windows machine and starts the backend before frontend development begins. The process must be safe to run more than once. It must detect the current system state and must not delete existing databases or change another application's SQL Server setup without permission.

### 7.1 Windows Bootstrap Entry Points

- [x] **`cloud_backend/scripts/install.ps1`**
    - Check that the operating system is Windows and that the script runs with administrator rights.
    - Check required tools, network access, available disk space, and the project files (`pyproject.toml`, `uv.lock`, and `.python-version`).
    - Create a bootstrap lock so two installation processes cannot run at the same time.
    - Install `uv` from an official source if it is missing, then refresh the current PowerShell process environment.
    - From the backend project directory, run `uv python install` to install the Python version pinned in `.python-version`.
    - Run `uv sync --locked` before checking or installing SQL Server so all backend dependencies are ready first.
    - Start the Python bootstrap orchestrator with the prepared uv environment.
    - Write installation logs to a known local log directory. Never write passwords or other secrets to logs.
    - Run the SQL Server, database, migration, seed, and environment setup steps in order.
    - Stop immediately when a required step fails and show the failed step and its log location.
    - Finish provisioning without launching Uvicorn from the elevated process. Show the command to run `start.ps1` as a normal user.
- [x] **`cloud_backend/scripts/start.ps1`**
    - Start the backend as a normal user. Do not require administrator rights for normal application startup.
    - Check whether this backend is already running before starting Uvicorn.
    - Check the configured API port and report a clear error if another process owns it.
    - Start Uvicorn and wait for the backend health check before reporting that the server is ready.
- [x] **`cloud_backend/scripts/stop.ps1`**
    - Stop only the backend process started by this project.
    - Allow the application to shut down cleanly and release its instance lock.
- [x] **`cloud_backend/scripts/status.ps1`**
    - Show the backend process and health status.
    - Show the selected SQL Server instance, service status, and SQL connection status.

### 7.2 Python Runtime & Project Dependencies

- [x] **`cloud_backend/bootstrap/runtime.py`**
    - Verify that `uv` is available and that the current process can find it. Do not overwrite the user's full `PATH` value.
    - Read the required Python version from the existing project `.python-version` file.
    - Verify that `uv` selected the pinned version and manages the project Python runtime. Do not install or manage a separate system Python version.
    - Verify that `uv sync --locked` completed and that the project environment can import its required packages.
    - Fail if `.python-version`, `pyproject.toml`, or `uv.lock` is missing or invalid.

### 7.3 SQL Server Instance Discovery

- [x] **`cloud_backend/bootstrap/sql_discovery.py`**
    - Discover all installed SQL Server instances from Windows services and SQL Server registry entries.
    - Detect the default instance (`MSSQLSERVER`), `SQLEXPRESS`, and any other named instances. Do not check only two fixed names.
    - Read the SQL Server version, edition, instance name, service name, and service status.
    - Check whether each instance supports the backend's required SQL features and has SQL Authentication enabled.
    - Check its TCP/IP status, configured port, and whether the port is reachable.
    - Select a compatible instance that is already configured for safe local access and SQL Authentication.
    - Do not silently enable TCP, change authentication, open firewall ports, or restart an existing instance used by other applications.
    - If an existing instance needs a disruptive change, stop and report the required action instead of changing it without permission.

### 7.4 SQL Server Installation

- [x] **`cloud_backend/bootstrap/sql_installer.py`**
    - Install SQL Server 2025 Developer with Winget only when no compatible instance is available.
    - Install a dedicated named instance (for example, `CLOUDCORE`) instead of taking over an existing default instance.
    - Use SQL Server Setup configuration options for unattended installation, including the Database Engine and Mixed Mode authentication.
    - Create a strong bootstrap SQL administrator credential. Do not use the `sa` account as the backend application account.
    - Protect temporary setup files that contain credentials and remove them after installation.
    - Wait for setup to finish and verify that the expected SQL Server service and instance exist.

### 7.5 SQL Server TCP, Service & Health Checks

- [x] **`cloud_backend/bootstrap/sql_configurator.py`**
    - Configure TCP/IP for a newly installed dedicated instance.
    - Use a fixed TCP port. Prefer `1433` only when it is available; otherwise select and record another free fixed port.
    - Disable dynamic port assignment for the selected instance and verify the final port configuration.
    - Use SQL Server configuration tools rather than editing undocumented registry values directly.
    - Add a Windows Firewall inbound rule only when remote machines must connect. Limit the rule to the required remote addresses. Local backend-to-database traffic must not require an inbound firewall rule.
    - Restart the SQL Server service only when a configuration change requires it.
- [x] **`cloud_backend/bootstrap/sql_health.py`**
    - Start the selected SQL Server service when it is stopped and wait until Windows reports it as running.
    - Check that the configured TCP port is listening.
    - Connect to the instance using SQL Authentication and run `SELECT 1`.
    - Allow a bounded startup wait and one additional start/retry attempt. Abort the bootstrap if the service or SQL connection still fails.
    - Include the service name, instance name, port, and useful error details in the log. Never log credentials.

### 7.6 Database & Login Provisioning

- [x] **`cloud_backend/bootstrap/database_provisioner.py`**
    - Connect to the SQL Server system database (`master`) with the temporary bootstrap administrator credentials.
    - Create `CloudCore` only when it does not exist.
    - Create `CloudTelemetry` only when it does not exist.
    - Never drop, recreate, or clear an existing database during a normal bootstrap run.
    - Create a dedicated SQL login for the backend application. Do not use the bootstrap administrator or `sa` in application connection strings.
    - Create the matching database users and grant only the permissions needed by the backend.
    - Verify that the application login can connect to both databases and perform the required operations.
    - Keep Core and Telemetry database provisioning separate so a failure in one step is reported clearly.

### 7.7 Schema Migrations & Seed Data

- [x] **`cloud_backend/bootstrap/migration_runner.py`**
    - Run the Core database migrations against `CloudCore`.
    - Run the Telemetry database migrations against `CloudTelemetry`.
    - Use Alembic migration revisions as the source of truth for database schema changes. Do not use `Base.metadata.create_all()` as the production setup mechanism.
    - Keep the migration configuration for each database clear and separate.
    - Verify the expected tables, indexes, and constraints after migration.
- [x] **`cloud_backend/bootstrap/seed_runner.py`**
    - Insert required initial seed data only when it is missing.
    - Make seed operations idempotent by using stable identifiers and database constraints where appropriate.
    - Verify the required seed records after insertion.
    - Never overwrite user-created data during a repeated bootstrap run.

### 7.8 Environment File Management

- [x] **`cloud_backend/bootstrap/env_manager.py`**
    - Build the `CORE_DB_URL` and `TELEMETRY_DB_URL` values for `CloudCore` and `CloudTelemetry` using the selected instance host and fixed port.
    - Safely encode usernames and passwords when building SQLAlchemy connection URLs.
    - Write the application SQL login credentials, not the bootstrap administrator credentials, to `.env`.
    - Preserve unrelated existing `.env` values. Update only the database settings managed by the bootstrap process.
    - Write the new file safely without creating an additional backup file, and restrict access to the file where supported.
    - Confirm that `.env` is excluded from Git and never print its secrets to the terminal or logs.
    - Write database URLs only after both databases, migrations, seeds, and connection checks succeed.

### 7.9 Backend Instance Lock & Startup

- [x] **`cloud_backend/bootstrap/instance_lock.py`**
    - Use a Windows named mutex to prevent two copies of this backend from running at the same time.
    - Keep the backend mutex alive for the full lifetime of the server process. Release it during normal shutdown; let Windows release it if the process crashes.
    - Use a separate lock for the bootstrap installer so installation and provisioning cannot run concurrently.
    - If the mutex is already held, report that the backend is running and do not start another copy.
    - Check the API port separately. If another, unrelated process owns it, stop and report the conflict instead of terminating that process.
    - Run Uvicorn with one worker and without reload when using the process-level mutex.
- [ ] **`cloud_backend/src/cloud_backend/main.py` or health router**
    - Provide a lightweight health endpoint if one does not already exist.
    - Verify that the application starts and can reach both databases before reporting readiness.
- [x] **`cloud_backend/bootstrap/orchestrator.py`**
    - Run the bootstrap steps in order: preflight, runtime, SQL discovery/install, SQL configuration, SQL health, database provisioning, migrations, seeds, and environment setup.
    - Track each step's result and write structured logs.
    - Check the real system state before repeating a completed step. A saved state file may help with diagnostics, but it must not replace real checks.
    - Make every step safe to retry. Never assume that a failed run left the machine unchanged.
    - Return success only after both databases, migrations, seeds, application credentials, and environment settings pass their checks.
    - Leave Uvicorn startup to `start.ps1`, which runs as a normal user after elevated provisioning is complete.

### 7.10 Bootstrap Verification

- [x] **`cloud_backend/tests/bootstrap/`**
    - Test bootstrap password retry behavior and environment-file preservation.
    - Test duplicate instance-lock rejection and lock release.
    - Test backend health and the existing backend regression suite.
    - Real SQL Server installation, service restart, and PowerShell lifecycle tests remain machine-level verification items.

---

## Phase 8: Frontend Services & Keyring

- [ ] **`cloud_frontend/src/cloud_frontend/services/auth_manager.py`**
    - Store JWT Access Token in application memory only.
- [ ] **`cloud_frontend/src/cloud_frontend/services/keyring_store.py`**
    - Save and load 30-day Refresh Token from OS Keyring.
- [ ] **`cloud_frontend/src/cloud_frontend/services/api_client.py`**
    - Build HTTP client with `httpx` to send requests and stream files.
- [ ] **`cloud_frontend/src/cloud_frontend/services/sse_client.py`**
    - Build SSE client with `httpx-sse` for admin live metrics updates.

---

## Phase 9: Frontend TUI (CLI & UI)

### 9.1 CLI Arguments & Themes

- [ ] **`cloud_frontend/src/cloud_frontend/cli/args.py`**
    - Parse CLI flags (`--admin`).
- [ ] **`cloud_frontend/src/cloud_frontend/ui/styles/theme.py`**
    - Define **Autumn Dark** color variables (`#292522`, Surface, Raised, Text, Status colors).

### 9.2 Custom Widgets

- [ ] **`cloud_frontend/src/cloud_frontend/ui/widgets/header.py`**
    - Display title `Cloud Store`, connection state, and username.
- [ ] **`cloud_frontend/src/cloud_frontend/ui/widgets/storage_bar.py`**
    - Render progress bar for used, reserved, and available quota.
- [ ] **`cloud_frontend/src/cloud_frontend/ui/widgets/file_table.py`**
    - Render interactive table of user files.
- [ ] **`cloud_frontend/src/cloud_frontend/ui/widgets/metrics_card.py`**
    - Render system metrics (CPU, RAM, Disk, Net) card widgets for admin.

### 9.3 Screens

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

### 9.4 Frontend Entry Point

- [ ] **`cloud_frontend/src/cloud_frontend/main.py`**
    - Entry point for `uv run cloud` and `uv run cloud --admin`.

---

## Phase 10: Tests

- [ ] **`cloud_backend/tests/`**
    - Unit tests for security (Argon2id, JWT, TOTP).
    - Integration tests for upload reservation and quota calculations.
- [ ] **`cloud_frontend/tests/`**
    - Tests for keyring store and API client helpers.
