# Install

This covers Milestones 1-5: building a Debian 13 (trixie) mini PC into a `cage` + Chromium kiosk
with the room's camera and speakerphone pinned as defaults, running the home screen and control
service driven by the room's real Microsoft 365 calendar, with a watchdog, nightly reboot,
auto-return-to-home and a screen on/off schedule. Later milestones (hardening, monitoring) will
extend this document.

## 1. Install Debian 13 on the device

- Use the Debian 13 (trixie) network-install image.
- Choose a **minimal install**: no desktop environment, no display manager.
- Select "SSH server" if you want remote management; nothing else from the task selector.
- Create an admin account with `sudo` access — this is the Ansible connection account, not the
  kiosk account (Ansible creates the `kiosk` user itself).
- Wired Ethernet is preferred; set a static IP or DHCP reservation for the device.

No other manual steps are required. Everything else is applied by the Ansible playbook.

## 2. Prepare the control machine

On the machine you'll run Ansible from:

```sh
sudo apt install ansible
```

Clone this repository, then copy the example inventory and adjust it for your device:

```sh
cp ansible/inventory.example.yml ansible/inventory.yml
```

Edit `ansible/inventory.yml` with the device's hostname/IP and SSH connection details. Add a
`ansible/host_vars/<hostname>.yml` file for any per-room overrides (see
`ansible/group_vars/rooms.yml` for what can be overridden — e.g. `room_name`).

Before running the playbook, identify the room's camera and speakerphone and set
`av_camera_vendor_id`/`av_camera_product_id`/`av_speakerphone_vendor_id`/
`av_speakerphone_product_id` in that `host_vars` file — see `docs/HARDWARE.md`. The playbook
applies without these, but audio/video device pinning won't do anything useful until they're set
to the real hardware's IDs.

Also complete the Microsoft 365 side (room mailbox, app registration, certificate) per
`docs/M365-SETUP.md`, then set `graph_tenant_id`, `graph_client_id`, `room_mailbox_upn` and the
vaulted certificate/key in that `host_vars` file — see `docs/OPERATIONS.md`. Without these, the
device still boots to a working home screen; it just shows no meetings (calendar polling stays
disabled rather than failing).

## 3. Run the playbook

```sh
cd ansible
ansible-playbook -i inventory.yml site.yml --ask-become-pass
```

This is idempotent — running it again should report no changes.

## 4. Verify

- Reboot the device: `sudo reboot`.
- It should boot directly to a fullscreen Chromium window showing the OpenRoom home screen (room
  name, clock, today's meetings from the room's calendar), with no login prompt, desktop, or
  window chrome visible.
- Confirm there's no way to reach a TTY login prompt, virtual console switch, or window manager
  from the kiosk screen.
- Run `openroom-avtest` and check the report (see `docs/HARDWARE.md`).
- Unplug and replug the camera and speakerphone; confirm they're still picked up without a
  reboot.
- Book a test Teams meeting on the room's calendar, confirm it appears on the home screen, tap
  Join, confirm it opens with no permission prompts, then use the "Leave & Home" button Teams
  shows to return to the home screen (see `docs/OPERATIONS.md`).
- `curl http://127.0.0.1:8080/health` from the device should return `{"status": "ok", ...}`,
  including calendar poll status.
- Confirm the "offline" banner appears if you temporarily block the device's access to
  `graph.microsoft.com` (e.g. in `/etc/hosts` or a firewall rule), and that the last-known
  meetings keep showing rather than disappearing.
- During a joined meeting, use Teams' own leave/hang-up control (not the injected "Leave & Home"
  button) and confirm the device auto-returns to the home screen within
  `resilience_poll_interval_seconds`.
- Stop `openroom-control.service` (`sudo systemctl stop openroom-control.service`) and confirm
  `openroom-watchdog.timer` restarts the kiosk within about a minute (see `docs/OPERATIONS.md`
  for exact timing) — check `journalctl -t openroom-watchdog`.
- Confirm `openroom-screen-schedule.timer`, `openroom-nightly-reboot.timer` and
  `openroom-watchdog.timer` are all active: `systemctl list-timers 'openroom-*'`.

## What's not covered yet

Firewall/hardening and monitoring arrive in later milestones and will be documented here as they
land.
