# CLI Design

## 1. Overview

Cloud is a CLI tool with a Terminal User Interface (TUI).

It has two interfaces:

- User Interface
- Admin Interface

Both interfaces use the same layout style and color theme.

## 2. Commands

- `uv run cloud` opens the User Interface.
- `uv run cloud --admin` opens the Admin Interface.

The `--admin` option does not give admin access. The server checks the user's role.

## 3. Authentication

- The client checks the access token first.
- The client uses the rotating refresh token when the access token expires.
- The login screen opens when the refresh token is not valid.
- Refresh tokens are stored in the Windows keyring for up to 30 days.
- A successful refresh replaces the stored keyring token with the new token.
- The login screen asks for a username, password, and 6-digit TOTP code.
- `uv run cloud` opens the user dashboard, including for an admin account.
- `uv run cloud --admin` requires an admin account before opening the Admin Interface.

## 4. User Interface

### Header

- Show the product name: `CloudVault`.
- Show the connection status.
- Show only the username.
- Do not show a `USER` label.

### Storage Information

Show:

- Storage used.
- Storage quota.
- Available storage.

All sizes are displayed in bytes with readable units (KB, MB, GB).

### File List

Show the user's files in a table.

| Field       | Description          |
| ----------- | -------------------- |
| File ID     | Unique file ID       |
| File Name   | Original file name   |
| File Size   | File size            |
| Extension   | File extension       |
| Uploaded At | Upload date and time |

- Show the newest files first.
- Support pagination.
- Do not show files that are being deleted.

### Actions

- Upload adds a new file.
- Download saves the selected file to the local device.
- Remove deletes the selected file.
- Ask for confirmation before Remove.
- Show upload progress during an upload.
- Show clear success or error messages.
- Disable Download and Remove when no file is selected.
- Accept either an existing download directory or an explicit target file path.
- Verify streamed download completion before reporting success.

### Keyboard Shortcuts

- `U (Upload)`
- `D (Download)`
- `R (Remove)`
- `L (Logout)`
- `Q (Quit)`

`Q` exits without clearing the keyring. `L` revokes the refresh-token session,
clears the keyring, and requires login on the next start.

## 5. Admin Interface

### Header

- Show the product name: `CloudVault`.
- Show the connection status.
- Show only the admin username.
- Do not show an `ADMIN` label.

### Navigation

The Admin Interface has five pages:

- Dashboard
- Sessions
- Telemetry
- User Register
- Users

### Dashboard

Show application metrics:

- Active sessions.
- Active uploads.
- Total users.
- Total files.
- Total storage used.

Show system metrics:

- CPU usage.
- RAM usage.
- Disk usage.
- Network receive speed.
- Network send speed.

Show the number of telemetry events per minute.

Show the latest telemetry events below the metrics.

Update system metrics every 2 seconds while the Admin Dashboard is open.

Update application metrics when relevant events occur.

### Sessions

Show active sessions only.

Display these fields:

| Field         | Description             |
| ------------- | ----------------------- |
| Session ID    | Unique session ID       |
| User ID       | Session owner ID        |
| Username      | Session owner name      |
| Client IP     | Client IP address       |
| Started At    | Session start time      |
| Last Activity | Last user activity time |

- Remove a session from the list when it ends.
- Do not show expired or ended sessions.
- Update the list when session events arrive.

### Telemetry

Show telemetry events as they arrive.

Display these fields:

| Field      | Description                      |
| ---------- | -------------------------------- |
| Event ID   | Unique event ID                  |
| Event Type | Type of event                    |
| User ID    | Related user ID, if available    |
| Session ID | Related session ID, if available |
| Client IP  | Client IP address, if available  |
| Event Time | Event date and time              |

Allow the admin to filter events by:

- Event type.
- User ID.
- Date range.

Show the newest events first.

Telemetry includes successful and failed operations, such as login, logout, upload, download, file deletion, and session events.

### User Register

Allow the admin to create a user.

The process:

1. Enter a username and initial password.
2. Create the user account.
3. Start TOTP setup.
4. Display the TOTP QR code.
5. Ask the user to scan the QR code and enter the first 6-digit code.
6. Confirm the TOTP setup.

A user cannot log in until TOTP setup is complete.

### Users

Show all registered users in a table.

Display these fields:

| Field         | Description           |
| ------------- | --------------------- |
| User ID       | Unique user ID        |
| Username      | User name             |
| Role          | User role             |
| Storage Quota | Maximum storage size  |
| Created At    | Account creation date |

Allow the admin to update a user's storage quota.

Show the quota editor after a user row is selected. The editor accepts a new quota
in bytes and enables the update action only for a selected user.

Allow normal deletion only when the user has no files or session history. Provide a
force-delete action for standard users that removes their physical files and related
records. Admin accounts and the current admin cannot be deleted.

Do not allow a quota smaller than the user's current storage usage plus active upload reservations.

## 6. Color Theme

Use the **Autumn Dark** theme. Use warm, dark, and soft colors. Do not use bright colors for large areas.

| Name       | Color     | Use                           |
| ---------- | --------- | ----------------------------- |
| Background | `#292522` | Main terminal background      |
| Surface    | `#34302C` | Panels                        |
| Raised     | `#403A36` | Selected rows and cards       |
| Foreground | `#ECE1D7` | Main text                     |
| Secondary  | `#C1A78E` | Secondary text                |
| Muted      | `#867462` | Help text and details         |
| Blue       | `#A3A9CE` | Upload and information        |
| Green      | `#85B695` | Download and success          |
| Red        | `#D47766` | Remove and errors             |
| Yellow     | `#EBC06D` | Warnings and important values |

### Color Rules

- Upload is always blue.
- Download is always green.
- Remove is always red.
- Success messages are green.
- Error messages are red.
- Warning messages are yellow.
- Information messages are blue.
- Use colors only when they show meaning.

## 7. Layout Rules

- Keep the interface simple and easy to read.
- Use the same colors and layout rules on both interfaces.
- Use clear text labels for actions and status messages.
- Do not use emojis or decorative icons.
- Keep important information easy to find.
- Display dates and times in the user's local time.
- Display file sizes with readable units.
- Show loading, empty, disconnected, and error states clearly.
