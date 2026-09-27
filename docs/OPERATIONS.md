# Operations

## ⚠ Before applying the hardening role

`roles/hardening` disables SSH password authentication and restricts SSH to
`hardening_ssh_allowed_subnet`. **Before running the playbook against a real device**:

1. Confirm your SSH public key is already in the admin account's `~/.ssh/authorized_keys` and
   that you can log in with it (not a password) right now.
2. Set `hardening_ssh_allowed_subnet` in `ansible/host_vars/<hostname>.yml` to the real subnet
   you'll be managing this device from — the default (`192.0.2.0/24`, an RFC 5737 TEST-NET range)
   deliberately matches no real network, so forgetting to set it locks out SSH entirely rather
   than leaving it open.

An existing SSH session survives the nftables/sshd reload within the same `ansible-playbook` run
(established connections are explicitly allowed), so you won't be cut off mid-run — but the
*next* connection attempt, from anywhere outside that subnet or without a key, will fail. If you
do lock yourself out, you'll need local/console access to the device to fix `/etc/nftables.conf`
or `/etc/ssh/sshd_config.d/99-openroom-hardening.conf`.

## Hardening

- **Firewall**: `nftables`, default-deny inbound. Only loopback, established/related connections,
  ICMP echo, and SSH (port 22, from `hardening_ssh_allowed_subnet` only) are allowed in. If
  `monitoring_node_exporter_enabled` is true, its port (`monitoring_node_exporter_port`, default
  9100) is allowed from the same subnet. Outbound is unrestricted — Graph, Teams and Microsoft
  sign-in all need arbitrary outbound HTTPS, and there's no fixed IP range worth allow-listing for
  those. IPv6 SSH is not explicitly allowed, so it's blocked by the default-deny policy; add a
  rule yourself if your management network needs IPv6.
- **SSH**: key-only (`PasswordAuthentication no`), no root login (`PermitRootLogin no`), via
  `/etc/ssh/sshd_config.d/99-openroom-hardening.conf`.
- **USB storage**: blocked entirely via `/etc/modprobe.d/openroom-blacklist-usb-storage.conf`
  (blacklists the `usb_storage` kernel module). Doesn't affect the configured camera (`uvcvideo`),
  audio (`snd-usb-audio`), or a USB keypad/remote (`usbhid`) — those are separate kernel modules.
- **Full-disk encryption / Secure Boot**: deliberately **not automated** — both need decisions
  made at OS install time (LUKS partitioning, TPM enrollment via `systemd-cryptenroll`, a Secure
  Boot signing pipeline for the kernel) that can't be safely retrofitted onto an already-installed
  system via Ansible. If you want these, set them up during the Debian install itself, before
  running this playbook; see your organisation's disk-encryption/Secure Boot standard for the
  specifics — this project doesn't prescribe one.
- **Minimal package set**: the Debian minimal + SSH-server-only install profile from
  `docs/INSTALL.md` is the baseline; the `hardening` role additionally runs `apt autoremove` to
  clear orphaned dependencies. No project role adds packages beyond what each component needs.

### Verifying the kiosk is actually locked down

- From another machine, confirm `nmap`/`ssh` against any port other than 22 (and, if enabled,
  9100) from within the management subnet gets nothing back, and that 22 itself is refused from
  outside that subnet.
- On the device, try to get to a shell from the kiosk screen (Ctrl+Alt+F2, Alt+Tab, right-click,
  etc.) — none should work; `getty@tty1` is masked and cage has no window chrome.
- Try navigating (via the URL bar — there isn't one in kiosk mode, so this really means: check the
  managed policy) to any site outside `URLAllowlist`; Chromium should show its own "blocked by
  administrator" page rather than the real site.
- Plug in a USB flash drive; confirm no storage device appears (`lsblk` shouldn't show it) while
  the configured camera/speakerphone/keypad continue working.

## Monitoring

- `/health` (`http://127.0.0.1:8080/health`) now returns `status`, `state` (home/in_meeting),
  `calendar_offline`, `calendar_last_success` (epoch seconds, `null` if never succeeded),
  `camera_present` (checks `/dev/openroom-camera` exists — the AV role's udev symlink, present
  only when the configured camera is actually plugged in), `audio_present` (checks
  `/proc/asound/cards` is non-empty — a presence signal, not a full diagnostic; use
  `openroom-avtest` for that), and `uptime_seconds` (this service instance's own uptime, so a
  recent watchdog-triggered restart is visible here).
- `prometheus-node-exporter` runs when `monitoring_node_exporter_enabled` (default true), exposing
  host-level metrics on `monitoring_node_exporter_port` (default 9100) — firewalled to
  `hardening_ssh_allowed_subnet` same as SSH. There's no OpenRoom-specific Prometheus exporter for
  `/health`'s own fields; scrape/poll `/health` directly if you want those in a dashboard.

## Control service

`openroom-control.service` runs the FastAPI app from a pinned virtualenv at
`/opt/openroom/venv`, as the unprivileged `openroom-control` system user, listening on
`127.0.0.1:8080` only. Logs go to journald as usual for a systemd service:

```sh
journalctl -u openroom-control.service -f
```

The service never logs join URLs, passcodes, tokens, or attendee lists — only high-level actions
(e.g. "joining meeting id=<event id>").

### Configuration

Set per-room in `ansible/host_vars/<hostname>.yml`:

- `room_name` — shown on the home screen.
- `graph_tenant_id`, `graph_client_id`, `room_mailbox_upn`, plus the vaulted
  `graph_client_certificate_pem`/`graph_client_private_key_pem` — see `docs/M365-SETUP.md`.
  Calendar polling stays disabled (not crashing) until these are set.
- `show_meeting_subject` — `true` shows the real subject; `false` shows just the organiser's
  name instead. Meetings marked "Private" in Outlook/Teams always show as "Private" regardless.
- `calendar_poll_interval_seconds` (default 60) and `calendar_timezone` (default
  `Europe/London` — set to the room's actual timezone).

### Calendar behaviour

- Polls the room mailbox's calendar view once per interval. On success, the result is cached to
  `/opt/openroom/state/calendar-cache.json` and served from memory; on failure (Graph
  unreachable, auth failure, etc.), the **last-known-good** data keeps being served and
  `/api/today`'s `offline` field is set, which the home screen shows as a discreet banner. The
  cache file means this survives a service restart during an outage too, not just an in-memory
  blip.
- Join links: `onlineMeeting.joinUrl` is used where Graph provides it; otherwise the event body is
  searched for a `teams.microsoft.com`/`teams.live.com` link. Any other link (e.g. Zoom) is
  ignored — that meeting shows in the list with no Join button.
- `/api/join/{id}` looks the meeting up in the cache by its Graph event ID; a meeting with no
  extracted Teams link returns 400 rather than navigating anywhere.

### Manually exercising Join/Leave/Home

With the service running (and Chromium reachable at `127.0.0.1:9222`), find a meeting ID from
`/api/today` first (there's no calendar-less hard-coded demo meeting any more as of Milestone 4):

```sh
curl http://127.0.0.1:8080/api/today
curl -X POST http://127.0.0.1:8080/api/join/<meeting id from above>
curl -X POST http://127.0.0.1:8080/api/home
curl http://127.0.0.1:8080/health
```

## Known-unverified pieces (check first on real hardware)

Same treatment as the AV role in Milestone 2 — these are built to spec but haven't been run
against a real Chromium/Debian install in this environment:

- **`chromium --headless --pack-extension`**: the `control` role uses Chromium's own extension
  packer to produce the signed CRX for the "Leave & Home" extension, run during provisioning
  (`ansible/roles/control/handlers/main.yml`). Whether this works unattended on a Debian minimal
  install with no display server running is unverified. If it fails, check
  `journalctl`/Ansible output for the exact Chromium error; a virtual framebuffer (`xvfb-run`)
  may be needed.
- **Chromium's extension ID derivation** (`scripts/openroom-extension-id.py`): the algorithm
  (SHA-256 of the DER `SubjectPublicKeyInfo`, first 16 bytes, nibbles mapped `0-9,a-f → a-p`) is
  Chromium's documented behaviour, and the script's output shape has been checked offline (32
  chars, alphabet `a-p`), but the *actual* ID Chromium assigns the packed CRX hasn't been
  cross-checked against this script's output on a real install.
- **Remote debugging flags**: `--remote-debugging-port=9222 --remote-debugging-address=127.0.0.1`
  are passed to Chromium in `roles/kiosk/templates/openroom-kiosk.service.j2`. Recent Chromium
  versions have tightened DevTools Protocol access (e.g. `Host`/`Origin` header checks against
  DNS-rebinding); if `control/app/cdp.py`'s requests to `127.0.0.1:9222` start failing on the
  installed Chromium version, check whether `--remote-allow-origins` needs adding.
- **`/api/join-by-id`**: navigates to Teams' own `https://teams.microsoft.com/meet` page rather
  than a constructed deep link (Teams doesn't publish a stable URL format for an ID+passcode
  join). Confirm this URL is still correct once tested against a live Teams session.
- **Graph certificate auth end-to-end**: `control/app/graph_client.py`'s certificate-credential
  flow has been checked against a real Microsoft identity platform endpoint (constructing the
  client performs real OIDC tenant discovery — see below), but only with a throwaway self-signed
  certificate and no real app registration, since none exists for this project. Confirm a real
  cert uploaded per `docs/M365-SETUP.md` actually authenticates once a tenant is available.
- **`msal.ConfidentialClientApplication` makes a network call at construction time**, not just at
  token acquisition — it performs OIDC tenant discovery immediately. `CalendarPoller` in
  `control/app/calendar.py` is deliberately written to build the client lazily inside the poll
  loop's try/except (not at import/startup time) specifically because of this — a network blip
  during boot must not crash the whole service. This is covered by
  `control/tests/test_calendar_poller.py`.
- **Application Access Policy scoping**: `docs/M365-SETUP.md` step 4 restricts the Graph app to
  room mailboxes only, but this has not been tested against a real tenant — CLAUDE.md's
  acceptance criteria explicitly call for verifying and documenting that the app cannot read a
  non-room mailbox. Do that test and record the result before relying on it.

## Resilience (Milestone 5)

### Auto-return to home

A background watcher (`control/app/resilience.py`) checks every `resilience_poll_interval_seconds`
(default 10s) while a meeting is joined, and returns to the home screen (clearing session storage
first, same as the manual Leave & Home button) when either:

- the active tab's URL no longer looks like it's on `teams.microsoft.com`/`teams.live.com` —
  covers the case where someone uses Teams' own hang-up/leave control; or
- the meeting's scheduled end time (from the calendar) plus `meeting_ended_grace_minutes`
  (default 5) has passed.

The time-based path is **unconditional** — it does not check whether the room is actually still
in use, since that would need Teams-specific participant/DOM signals this project has no live
tenant to verify. An overrunning meeting will be returned home after the grace period even if
people are still in it; increase `meeting_ended_grace_minutes` per room if that's a problem.

### Watchdog

`openroom-watchdog.timer` runs `openroom-watchdog-check` every `updates_watchdog_interval_seconds`
(default 20s). It checks `http://127.0.0.1:8080/health` and Chromium's DevTools endpoint
(`http://127.0.0.1:9222/json/version`); after ~3 consecutive failures (~60s of sustained trouble,
not a single blip) it restarts `openroom-kiosk.service`, and after 3 such restarts within a
10-minute window it reboots instead. State is kept in `/run/openroom/` (tmpfs, resets on reboot).
This counting logic was dry-run tested offline with faked `curl`/`systemctl` before being wired
into Ansible — see the script's git history for the test transcript if you want to re-verify it.

### Nightly reboot

`openroom-nightly-reboot.timer` fires once daily at `updates_nightly_reboot_time` (default
`03:00`), checking `/health`'s `state` field first — if `in_meeting`, it skips that night's reboot
and logs why, rather than dropping an overnight call. `unattended-upgrades` is configured for
security updates only, with its own automatic reboot disabled (`Automatic-Reboot "false"`) so
this one timer is the single source of truth for reboot timing, rather than two independent
reboot triggers racing each other.

### Screen schedule

`openroom-screen-schedule.timer` runs every minute, as the `kiosk` user, using `wlr-randr` against
cage's Wayland output. Outside `screen_off_time`–`screen_on_time` (default `19:00`–`07:00`) the
screen turns off, **except**: it stays on (or wakes early) if a meeting is currently in progress,
or if the next calendar meeting starts within `screen_wake_before_minutes` (default 5) — read
from the control service's own `/api/today`, so no separate calendar access is needed here. The
on/off/wake-window decision logic was dry-run tested offline across daytime, out-of-hours,
in-meeting, imminent-meeting and overnight-wraparound cases before being wired into Ansible.

**Unverified**: this assumes cage's Wayland socket is named `wayland-1` (its default as the first
compositor instance) and that a plain `User=kiosk` systemd service can reach it via
`XDG_RUNTIME_DIR=/run/user/%U` — there's no real cage/Wayland session in this environment to
confirm that against. If the screen doesn't respond, check
`journalctl -u openroom-screen-schedule.service` for a `wlr-randr` connection error first.

## Manual Teams call test

See `docs/HARDWARE.md` for the manual-Chromium-session procedure — superseded day-to-day by the
control service's own Join button once a real meeting is on the room's calendar (Milestone 4).
