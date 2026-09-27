# OpenRoom

A reproducible, low-cost meeting room appliance that joins Microsoft Teams meetings from a fixed
room, built on a small x86 mini PC running Debian and open-source Linux components. See
[`CLAUDE.md`](CLAUDE.md) for the full specification and build plan.

OpenRoom is **not** a certified Microsoft Teams Rooms device. It joins meetings through the Teams
web client in a Chromium kiosk, signed in as a dedicated room resource account.

## Status

Work proceeds milestone by milestone (see `CLAUDE.md`). Current state:

- [x] Milestone 1 — Bare kiosk: Ansible builds Debian into a `cage` + Chromium kiosk showing a
      static placeholder page.
- [ ] Milestone 2 — AV
- [ ] Milestone 3 — Control service
- [ ] Milestone 4 — Calendar
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

See `CLAUDE.md` for the full target layout. As of Milestone 1:

```
openroom/
├── CLAUDE.md
├── README.md
├── ansible/
│   ├── site.yml
│   ├── inventory.example.yml
│   ├── group_vars/rooms.yml
│   └── roles/{base,kiosk,browser}/
├── control/
│   └── static/placeholder.html
└── docs/
    └── INSTALL.md
```
