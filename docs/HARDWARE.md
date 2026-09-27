# Hardware

## Tested devices

None yet. This build has not been run against real hardware — it has been developed and
validated (YAML/Jinja2 syntax, template rendering, shell syntax) on a non-Debian development
machine with no room camera or speakerphone attached. Treat the AV role as unverified until it's
been run on an actual device; please add an entry here once it has, including the mini PC model,
camera/speakerphone models, and any deviations from the defaults below.

## Identifying your camera and speakerphone

OpenRoom pins the room camera and speakerphone by USB vendor/product ID rather than relying on
enumeration order, which is not stable across reboots or hot-plug events.

1. Plug in the camera and speakerphone, then run:

   ```sh
   lsusb
   ```

2. Find your devices in the list, e.g.:

   ```
   Bus 001 Device 004: ID 046d:0825 Logitech, Inc. Webcam C270
   Bus 001 Device 005: ID 0d8c:0014 C-Media Electronics, Inc. USB Audio Device
   ```

   The four hex digits before the colon are the vendor ID, the four after are the product ID.

3. Set these in `ansible/host_vars/<hostname>.yml` for the room:

   ```yaml
   av_camera_vendor_id: "046d"
   av_camera_product_id: "0825"
   av_speakerphone_vendor_id: "0d8c"
   av_speakerphone_product_id: "0014"
   ```

## Camera controls (autofocus, exposure)

`openroom-av.service` applies `av_camera_format` (default 1280x720 MJPG) and any entries in
`av_camera_v4l2_controls` to the camera on boot and hot-plug. UVC control names differ between
camera generations (e.g. `focus_auto` vs `focus_automatic_continuous`, `exposure_auto` vs
`auto_exposure`), so nothing is guessed by default. On the real device:

```sh
v4l2-ctl --device=/dev/openroom-camera --list-ctrls
```

Then set the controls you need in `host_vars/<hostname>.yml`, e.g.:

```yaml
av_camera_v4l2_controls:
  - "focus_automatic_continuous=0"
  - "exposure_time_absolute=250"
```

## Echo cancellation

Leave `av_software_echo_cancel_enabled: false` (the default) if the speakerphone has hardware
echo cancellation — enabling PipeWire's software echo-cancel module on top of that causes
double-cancellation artefacts. Only set it `true` for a microphone/speaker pair with no hardware
AEC. This module's configuration (`ansible/roles/av/templates/10-openroom-echo-cancel.conf.j2`)
has not been validated against real hardware; check `pw-top`/`wpctl status` after enabling it to
confirm the virtual echo-cancel source/sink actually appear and Chromium picks them up.

## Running the AV smoke test

Once the playbook has been applied:

```sh
openroom-avtest
```

This plays a test tone, records five seconds of audio, plays the recording back, and captures a
still frame from the camera, printing a PASS/FAIL line per step and the paths to the recording
and still frame. It confirms the pipeline runs end-to-end — pull the files off with `scp` to
judge quality by ear/eye yourself.

## Manual Teams call test

This is done through the control service's own home screen rather than a throwaway Chromium
session: book a real Teams meeting on the room's calendar (see `docs/M365-SETUP.md` and
`docs/OPERATIONS.md` for getting the calendar connected), tap Join on the kiosk's home screen, and
confirm camera and microphone are active with no permission prompt (the managed policy's
`VideoCaptureAllowedUrls`/`AudioCaptureAllowedUrls` pre-grant both).
