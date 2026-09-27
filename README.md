# OpenRoom

A reproducible, low-cost meeting room appliance that joins Microsoft Teams meetings from a fixed
room, built on a small x86 mini PC running Debian and open-source Linux components.

OpenRoom is **not** a certified Microsoft Teams Rooms device. It joins meetings through the Teams
web client in a Chromium kiosk, signed in as a dedicated room resource account.

## Status

Feature-complete. Current state:

- **Bare kiosk**: Ansible builds Debian into a `cage` + Chromium kiosk.
- **AV**: camera and speakerphone pinned as PipeWire/WirePlumber defaults by USB vendor/product
  ID, `openroom-avtest` diagnostic command. Not yet verified on real hardware (see
  `docs/HARDWARE.md`).
- **Control service**: FastAPI home screen, DevTools Protocol Join/Leave/Home, "Leave & Home"
  Chromium extension. Some pieces unverified on real hardware (see `docs/OPERATIONS.md`).
- **Calendar**: Microsoft Graph integration with certificate auth, scoped to room mailboxes,
  offline caching with a last-known-good fallback. M365 tenant setup documented in
  `docs/M365-SETUP.md`; scoping and end-to-end auth unverified against a real tenant (see
  `docs/OPERATIONS.md`).
- **Resilience**: watchdog (restart kiosk after ~60s unhealthy, reboot after 3 restarts/10min),
  nightly reboot skipped during a meeting, auto-return to home on meeting end, screen on/off
  schedule with early wake for the next meeting. Counting/scheduling logic dry-run tested offline;
  screen control unverified against a real cage/Wayland session (see `docs/OPERATIONS.md`).
- **Hardening and monitoring**: `nftables` default-deny firewall (SSH/node-exporter restricted to
  a configurable management subnet), SSH key-only/no-root-login, USB storage blocked,
  `prometheus-node-exporter`, `/health` extended with camera/audio presence and uptime. **Read
  `docs/OPERATIONS.md`'s warning before applying** — it changes SSH access and can lock you out
  if misconfigured. Full-disk encryption/Secure Boot deliberately documented, not automated.
- **Documentation**: all docs (`INSTALL.md`, `HARDWARE.md`, `OPERATIONS.md`, `M365-SETUP.md`)
  cross-checked against the actual current Ansible variables/roles, with consolidated
  Logs/Re-authentication/Troubleshooting sections added to `OPERATIONS.md`. See "Verification
  status" below for exactly what has and hasn't been confirmed.

## Verification status

This entire build was developed without any target Debian hardware, installed Chromium, or a
real Microsoft 365 tenant available — see the notes above and `docs/OPERATIONS.md`'s
"Known-unverified pieces" for specifics. What **has** been verified in that environment:

- `pytest control/` — 40/40 passing, including tests that exercise real OIDC discovery against
  `login.microsoftonline.com` and an extension-ID derivation checked against a throwaway keypair.
- Every Ansible YAML file parses, and every Jinja2 template renders cleanly with the full merged
  `group_vars`/role-defaults variable set (not just hand-picked samples).
- The rendered `nftables` ruleset was checked against the real `nft` binary.
- The watchdog's failure-counting/reboot-threshold logic and the screen schedule's decision logic
  were both dry-run tested offline against faked `curl`/`systemctl`/`wlr-randr`.

What this means: **a fresh build following `docs/INSTALL.md` has not been run end-to-end.** The
first real deployment is that end-to-end test — expect to hit at least one of the specifically
flagged unverified items, and please update the relevant doc once you've confirmed or fixed it.

## Known limitations

Compared with a certified Teams Rooms system, this device does not provide: Proximity Join or
casting from laptops, the Teams Rooms console experience, Front Row layout, content cameras,
central management in the Teams Rooms Pro portal, or Microsoft support. It joins meetings as a
signed-in participant, not as a room system. It is suited to small huddle rooms and
budget-limited spaces, not boardrooms or large rooms.

## Repository layout

```
openroom/
├── README.md
├── ansible/
│   ├── site.yml
│   ├── inventory.example.yml
│   ├── group_vars/rooms.yml
│   └── roles/{base,kiosk,control,browser,av,updates,hardening,monitoring}/
├── control/
│   ├── app/            (FastAPI app: routes, state machine, CDP client, Graph calendar client,
│   │                     resilience watcher)
│   ├── static/          (home screen: index.html, theme.css, app.js)
│   ├── extension/      (Leave & Home Chromium extension)
│   ├── tests/
│   └── requirements.txt
├── scripts/
│   ├── openroom-avtest
│   ├── openroom-avtest-tone.wav
│   ├── openroom-extension-id.py
│   ├── openroom-watchdog-check
│   ├── openroom-nightly-reboot
│   └── openroom-screen-schedule
└── docs/
    ├── INSTALL.md
    ├── HARDWARE.md
    ├── OPERATIONS.md
    └── M365-SETUP.md
```
