# Install

This covers Milestones 1-2: building a Debian 13 (trixie) mini PC into a `cage` + Chromium kiosk
showing a static placeholder page, with the room's camera and speakerphone pinned as defaults.
Later milestones (control service, calendar, hardening, monitoring) will extend this document.

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

## 3. Run the playbook

```sh
cd ansible
ansible-playbook -i inventory.yml site.yml --ask-become-pass
```

This is idempotent — running it again should report no changes.

## 4. Verify

- Reboot the device: `sudo reboot`.
- It should boot directly to a fullscreen Chromium window showing the OpenRoom placeholder page,
  with no login prompt, desktop, or window chrome visible.
- Confirm there's no way to reach a TTY login prompt, virtual console switch, or window manager
  from the kiosk screen.
- Run `openroom-avtest` and check the report (see `docs/HARDWARE.md`).
- Unplug and replug the camera and speakerphone; confirm they're still picked up without a
  reboot.
- Do a manual Teams test call following `docs/HARDWARE.md` and confirm audio/video work with no
  permission prompts.

## What's not covered yet

The real home screen and calendar, firewall/hardening, automatic updates and monitoring all
arrive in later milestones and will be documented here as they land.
