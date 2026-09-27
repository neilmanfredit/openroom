# Operations

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

## Manual Teams call test (Milestone 2, still applicable)

See `docs/HARDWARE.md` — the manual-Chromium-session procedure there is superseded by the control
service's own Join button now that `control_demo_join_url` is set to a real meeting link.
