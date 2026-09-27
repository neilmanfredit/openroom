# CLAUDE.md — OpenRoom: Low-Cost Teams Meeting Room Device

## Purpose

Build a reproducible, low-cost meeting room appliance that joins Microsoft Teams meetings from a fixed room. It runs on a small x86 mini PC with open-source Linux, driving an all-in-one (AIO) monitor that has a built-in webcam, speaker and microphone (or a separate USB speakerphone).

The device should behave like an appliance: power on, show today's meetings for the room, one tap to join, return to the home screen when the meeting ends. No desktop, no file browser, no way for a user to wander off.

## Hard constraints

- This is **not** a certified Microsoft Teams Rooms device. Microsoft only supports Teams Rooms on certified Windows and Android hardware. Do not attempt to emulate, spoof or reverse-engineer the Teams Rooms client or its licensing.
- Meetings are joined through the **Teams web client** (teams.microsoft.com) in Chromium, signed in as a dedicated room resource account.
- Everything must be buildable from a clean Debian install using the Ansible playbook in this repo. No manual steps other than those listed in `docs/INSTALL.md`.
- Prefer packages from the Debian repositories. Where a Python dependency is needed, use a pinned virtual environment under `/opt/openroom`.
- UK English in all user-facing text, docs and comments.

## Target platform

| Item | Choice |
|---|---|
| OS | Debian 13 (trixie), minimal install, no desktop environment |
| Hardware | x86-64 mini PC, Intel N100/N150 class or better, 16 GB RAM, 256 GB SSD, wired Ethernet preferred |
| Display | AIO monitor over HDMI or USB-C; touch optional but supported |
| Camera | UVC USB webcam (built into the AIO monitor or standalone) |
| Audio | USB speakerphone or AIO built-in audio; hardware echo cancellation preferred |
| Compositor | `cage` (single-application Wayland kiosk) |
| Browser | Chromium from Debian repos, managed by enterprise policy |
| Audio stack | PipeWire + WirePlumber |
| Config management | Ansible |

## Architecture

```
systemd
 ├── openroom-control.service   (Python/FastAPI on 127.0.0.1:8080)
 │     ├── serves the home screen (static HTML/CSS/JS, no build step)
 │     ├── pulls room calendar from Microsoft Graph
 │     ├── drives Chromium via the DevTools Protocol (127.0.0.1:9222 only)
 │     └── exposes /health for monitoring
 ├── openroom-kiosk.service     (cage → Chromium, kiosk user, auto-login on tty1)
 ├── openroom-av.service        (one-shot: set default audio devices, lock camera settings)
 └── openroom-watchdog.timer    (restart kiosk if Chromium or control service stops responding)
```

### Flow

1. Boot → auto-login `kiosk` user on tty1 → `cage` starts Chromium in kiosk mode pointing at `http://127.0.0.1:8080/`.
2. Home screen shows room name, clock, current/next meeting, and today's list with a **Join** button per meeting that has a Teams join link.
3. Join → control service tells Chromium (via DevTools Protocol) to navigate to the meeting's join URL. Camera and microphone permissions are pre-granted by policy, so no prompts appear.
4. The control service watches the active tab URL. When the meeting ends (URL leaves the meeting route, or the scheduled end time passes by a configurable grace period with nobody in the call), it navigates back to the home screen and clears the meeting state.
5. A small, always-available **Leave & Home** control is injected into the Teams page by a local unpacked Chromium extension, so users can always get back.
6. Ad-hoc: a **Join by meeting ID** screen (meeting ID + passcode) using the Teams "join a meeting" web flow.

## Components to build

### 1. Ansible (`ansible/`)

- `site.yml` with roles: `base`, `kiosk`, `browser`, `av`, `control`, `hardening`, `updates`, `monitoring`.
- Inventory example for a single device; variables in `group_vars/rooms.yml` with per-room overrides in `host_vars/`.
- Idempotent. Running twice must produce no changes.
- Secrets (Graph client certificate, room account details) via Ansible Vault, never committed in plain text.

### 2. Kiosk session (`roles/kiosk`)

- Create a non-privileged `kiosk` user with no sudo and no password login.
- Auto-login on tty1 via a getty override; launch `cage` from the user's systemd service.
- Hide the cursor after inactivity; support touch input.
- Screen off out of hours (configurable schedule) and wake five minutes before the next booked meeting.

### 3. Browser policy (`roles/browser`)

Write managed policy JSON to `/etc/chromium/policies/managed/openroom.json`, including:

- `VideoCaptureAllowedUrls` and `AudioCaptureAllowedUrls` for `https://teams.microsoft.com` and `https://teams.live.com`
- `URLAllowlist` restricted to Microsoft sign-in and Teams domains plus `http://127.0.0.1:8080`; `URLBlocklist` of `*`
- Disable DevTools for users, downloads, printing, incognito, password manager, autofill, translate prompts, first-run and default-browser prompts
- Install the local "Leave & Home" extension via `ExtensionInstallForcelist` (self-hosted update manifest on localhost)
- Remote debugging bound to `127.0.0.1` only; confirm it is not reachable from the network

### 4. Audio and video (`roles/av`)

- PipeWire + WirePlumber for the `kiosk` user.
- Identify the speakerphone and camera by USB vendor/product ID from config; set them as default source and sink with WirePlumber rules. Do not rely on device enumeration order.
- If the audio device has hardware echo cancellation, do **not** enable software echo cancellation. Provide a config switch to enable the PipeWire echo-cancel module for devices without it.
- Use `v4l2-ctl` on boot and on hot-plug (udev rule) to fix resolution, disable auto-focus hunting if configurable, and set sensible exposure.
- Provide `openroom-avtest` command: plays a test tone, records five seconds, plays it back, and captures a still frame from the camera. Output a simple pass/fail report.

### 5. Control service (`control/`)

Python 3, FastAPI, Uvicorn, pinned `requirements.txt`, running as its own system user.

- **Calendar**: Microsoft Graph, client credentials flow with **certificate** authentication (no client secrets). Read the room mailbox's calendar view for today. Cache results; poll every 60 seconds; keep showing the last good data if Graph is unreachable, with a discreet "offline" indicator.
- **Join link extraction**: use `onlineMeeting.joinUrl` where present; fall back to parsing the body for a Teams join link. Ignore non-Teams links.
- **Browser control**: Chrome DevTools Protocol over websocket to navigate, read the current URL, and reset state. Clear session storage for the meeting between calls without logging the room account out.
- **Privacy**: show meeting subject only if the room's config allows; otherwise show organiser and time only. Private meetings always shown as "Private".
- **Endpoints**: `/` (home screen), `/api/today`, `/api/join/{id}`, `/api/join-by-id`, `/api/home`, `/health`.
- Structured logging to journald. Never log join URLs with passcodes, tokens or attendee lists.

### 6. Home screen (`control/static/`)

- Plain HTML, CSS and JavaScript. No framework, no build step.
- Readable from across a room: large clock, room name, current and next meeting, big touch targets.
- Theme file (`theme.css`) with colour, font and logo variables so it can be rebranded per site without code changes.
- Works at 1920×1080 and 1366×768; supports touch, mouse, and a USB numeric keypad or presenter remote (arrow keys + Enter).

### 7. Hardening (`roles/hardening`)

- `nftables` default deny inbound; allow SSH from a configurable management subnet only.
- SSH key-only authentication, no root login.
- Optional: full-disk encryption unlocked by TPM (`systemd-cryptenroll`), Secure Boot with signed kernel.
- USB storage blocked for the kiosk session (udev), while allowing the configured camera, audio and HID devices.
- Minimal package set; remove anything not required.

### 8. Updates and resilience (`roles/updates`)

- `unattended-upgrades` for security updates, applied overnight.
- Nightly reboot at a configurable time, skipped if a meeting is in progress.
- Watchdog timer: if `/health` fails or Chromium is not responding for 60 seconds, restart the kiosk service; after three failures in ten minutes, reboot.

### 9. Monitoring (`roles/monitoring`)

- Optional `prometheus-node-exporter`.
- `/health` returns JSON: service status, Graph last-success time, camera present, audio devices present, current state (idle/in-meeting), uptime.

## Microsoft 365 setup (document, do not automate)

Write `docs/M365-SETUP.md` covering:

1. Create a room resource mailbox and enable the account for sign-in.
2. Assign a licence that includes Teams and permits a signed-in user on uncertified hardware. Teams Rooms licences are for certified devices; confirm licensing with the organisation's Microsoft licensing contact before rollout.
3. App registration for Graph with the application permission `Calendars.Read`, certificate credential only.
4. **Restrict the app to room mailboxes only** using Exchange Online RBAC for Applications (or an Application Access Policy on older tenants). The app must not be able to read any user calendars.
5. Conditional Access: a policy for room accounts that suits a shared, fixed device (e.g. trusted network location), rather than excluding the account from MFA without compensating controls.
6. First sign-in procedure for the room account on the device, and how to re-authenticate when the session expires.

## Repository layout

```
openroom/
├── CLAUDE.md
├── README.md
├── ansible/
│   ├── site.yml
│   ├── inventory.example.yml
│   ├── group_vars/rooms.yml
│   └── roles/{base,kiosk,browser,av,control,hardening,updates,monitoring}/
├── control/
│   ├── app/            (FastAPI app, Graph client, CDP client, state machine)
│   ├── static/         (home screen, theme.css)
│   ├── extension/      (Leave & Home Chromium extension)
│   ├── tests/
│   └── requirements.txt
├── scripts/openroom-avtest
└── docs/
    ├── INSTALL.md
    ├── M365-SETUP.md
    ├── HARDWARE.md     (tested devices, known issues)
    └── OPERATIONS.md   (updates, logs, re-auth, troubleshooting)
```

## Milestones

Work through these in order. Use plan mode at the start of each milestone and confirm the plan before writing code.

1. **Bare kiosk** — Ansible builds Debian into a cage + Chromium kiosk showing a static page. Survives reboot.
2. **AV** — Camera and speakerphone pinned as defaults; `openroom-avtest` passes; a manual Teams test call has working audio and video with no permission prompts.
3. **Control service** — Home screen, DevTools Protocol navigation, Join/Leave/Home working with a hard-coded join URL.
4. **Calendar** — Graph integration with certificate auth, scoped to room mailboxes, offline caching.
5. **Resilience** — Watchdog, nightly reboot logic, auto-return to home, screen schedule.
6. **Hardening and monitoring** — Firewall, USB policy, `/health`, node exporter.
7. **Documentation** — All docs complete; a fresh build following `INSTALL.md` works end to end.

## Acceptance criteria

- Cold boot to home screen in under 60 seconds on N100-class hardware.
- Join from home screen to in-meeting in under 15 seconds, with camera and microphone active and no prompts.
- Device returns to home screen within 30 seconds of a meeting ending.
- Unplugging and replugging the camera or speakerphone recovers without a reboot.
- A user cannot reach a shell, file browser, settings page or non-allowlisted website from the kiosk.
- The Graph app cannot read any non-room mailbox (test and document the result).
- Re-running the Ansible playbook produces no changes.
- Unit tests for the calendar parser, join-link extraction and meeting state machine; `pytest` passes.

## Known limitations (state these in README.md)

Compared with a certified Teams Rooms system, this device does not provide: Proximity Join or casting from laptops, the Teams Rooms console experience, Front Row layout, content cameras, central management in the Teams Rooms Pro portal, or Microsoft support. It joins meetings as a signed-in participant, not as a room system. It is suited to small huddle rooms and budget-limited spaces, not boardrooms or large rooms.

## Working rules for Claude Code

- Ask before adding any dependency not in the Debian repositories.
- Do not store secrets in the repo, logs, or the browser profile outside what Chromium itself requires.
- Keep each role small and readable; comment the reason for non-obvious settings.
- After each milestone, update `docs/` and summarise what changed and what is still outstanding.
