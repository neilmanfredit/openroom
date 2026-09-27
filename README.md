# OpenRoom

A reproducible, low-cost meeting room appliance that joins Microsoft Teams meetings from a fixed
room, built on a small x86 mini PC running Debian and open-source Linux components.

OpenRoom is **not** a certified Microsoft Teams Rooms device. It joins meetings through the Teams
web client in a Chromium kiosk, signed in as a dedicated room resource account.

## Status

Work proceeds milestone by milestone. Current state:

- [x] Milestone 1 — Bare kiosk: Ansible builds Debian into a `cage` + Chromium kiosk.
- [x] Milestone 2 — AV: camera and speakerphone pinned as PipeWire/WirePlumber defaults by USB
      vendor/product ID, `openroom-avtest` diagnostic command. Not yet verified on real hardware
      (see `docs/HARDWARE.md`).
- [x] Milestone 3 — Control service: FastAPI home screen, DevTools Protocol Join/Leave/Home,
      "Leave & Home" Chromium extension. Some pieces unverified on real hardware (see
      `docs/OPERATIONS.md`).
- [x] Milestone 4 — Calendar: Microsoft Graph integration with certificate auth, scoped to room
      mailboxes, offline caching with a last-known-good fallback. M365 tenant setup documented in
      `docs/M365-SETUP.md`; scoping and end-to-end auth unverified against a real tenant (see
      `docs/OPERATIONS.md`).
- [ ] Milestone 5 — Resilience
- [ ] Milestone 6 — Hardening and monitoring
- [ ] Milestone 7 — Documentation

## Known limitations

Compared with a certified Teams Rooms system, this device does not provide: Proximity Join or
casting from laptops, the Teams Rooms console experience, Front Row layout, content cameras,
central management in the Teams Rooms Pro portal, or Microsoft support. It joins meetings as a
signed-in participant, not as a room system. It is suited to small huddle rooms and
budget-limited spaces, not boardrooms or large rooms.

## Repository layout

As of Milestone 4:

```
openroom/
├── README.md
├── ansible/
│   ├── site.yml
│   ├── inventory.example.yml
│   ├── group_vars/rooms.yml
│   └── roles/{base,kiosk,control,browser,av}/
├── control/
│   ├── app/            (FastAPI app: routes, state machine, CDP client, Graph calendar client)
│   ├── static/          (home screen: index.html, theme.css, app.js)
│   ├── extension/      (Leave & Home Chromium extension)
│   ├── tests/
│   └── requirements.txt
├── scripts/
│   ├── openroom-avtest
│   ├── openroom-avtest-tone.wav
│   └── openroom-extension-id.py
└── docs/
    ├── INSTALL.md
    ├── HARDWARE.md
    ├── OPERATIONS.md
    └── M365-SETUP.md
```
