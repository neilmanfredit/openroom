# Operations

## Control service

`openroom-control.service` runs the FastAPI app from a pinned virtualenv at
`/opt/openroom/venv`, as the unprivileged `openroom-control` system user, listening on
`127.0.0.1:8080` only. Logs go to journald as usual for a systemd service:

```sh
journalctl -u openroom-control.service -f
```

The service never logs join URLs, passcodes, tokens, or attendee lists — only high-level actions
(e.g. "joining meeting id=demo").

### Configuration

Set per-room in `ansible/host_vars/<hostname>.yml`:

- `room_name` — shown on the home screen.
- `control_demo_join_url` — Milestone 3 has no calendar yet (that's Milestone 4), so this single
  fixed URL stands in for a real meeting. Set it to a real Teams meeting join link to exercise
  Join/Leave/Home end-to-end.

### Manually exercising Join/Leave/Home

With the service running (and Chromium reachable at `127.0.0.1:9222`):

```sh
curl -X POST http://127.0.0.1:8080/api/join/demo
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

## Manual Teams call test (Milestone 2, still applicable)

See `docs/HARDWARE.md` — the manual-Chromium-session procedure there is superseded by the control
service's own Join button now that `control_demo_join_url` is set to a real meeting link.
