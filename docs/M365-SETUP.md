# Microsoft 365 setup

This is deliberately **not** automated by the Ansible playbook — it touches tenant-wide identity,
licensing and security posture, which should go through your organisation's normal change process
and be reviewed by whoever owns Microsoft 365 admin and security for the tenant. Do each step
below once per room, then feed the resulting values into `ansible/host_vars/<hostname>.yml` as
described at the end.

## 1. Create the room resource mailbox

In the Microsoft 365 admin center (or Exchange Online PowerShell), create a room resource
mailbox for each physical room, and enable it for sign-in (room mailboxes are sign-in disabled by
default):

```powershell
New-Mailbox -Room -Name "Brighton Huddle 1" -DisplayName "Brighton Huddle 1" `
    -UserPrincipalName room-brighton-1@example.onmicrosoft.com

# Room mailboxes are created with sign-in blocked; this device needs to sign in as the account
Set-User -Identity room-brighton-1@example.onmicrosoft.com -AccountDisabled $false
```

Set a strong, unique password for the account (or configure it for passwordless/certificate sign-in
per your tenant's standards) and record it somewhere your organisation's secrets management
covers — OpenRoom's own Ansible Vault is for the *Graph app's* certificate, not this account's
own sign-in credential.

## 2. Licensing

Assign a licence that includes Microsoft Teams and permits a normal signed-in user session —
this device signs into the Teams **web client** as a regular user, not as a certified Teams Rooms
system. **Microsoft Teams Rooms licences are for certified, Microsoft-validated hardware only**;
using one here would misrepresent the device to Microsoft's licensing terms. Confirm the right
licence SKU with your organisation's Microsoft licensing contact before rolling this out —
requirements and available SKUs change over time and by region/agreement.

## 3. App registration for Graph (certificate auth, no client secret)

Create an app registration (Entra ID admin center → App registrations → New registration):

- Supported account types: single tenant.
- No redirect URI needed (this is a daemon/service app using client credentials, not a
  user-interactive one).

Grant it exactly one **application** (not delegated) Graph permission:

- `Calendars.Read` — grant admin consent for the tenant.

Do not grant `Calendars.Read.All`-style broader permissions beyond what's needed, and do not add
any other permission — the goal is an app that can read calendar data and nothing else, further
scoped down to just the room mailboxes in step 4.

### Certificate credential (no client secret)

Generate a certificate for this app registration. On a secure admin workstation, **not** on the
kiosk device itself:

```sh
openssl req -x509 -newkey rsa:2048 -keyout graph-client-key.pem -out graph-client-cert.pem \
    -days 730 -nodes -subj "/CN=openroom-brighton-1"
```

Upload `graph-client-cert.pem` (the public certificate, not the key) to the app registration
under Certificates & secrets → Certificates. **Do not create a client secret** — this app should
have certificate credentials only, per CLAUDE.md's hard constraint on certificate-only auth.

Keep `graph-client-key.pem` (the private key) and `graph-client-cert.pem` secure; you'll encrypt
both into Ansible Vault in the last step below. Set a calendar reminder for renewal before the
certificate's expiry (730 days in the example above) — there's no automated rotation in this
build.

## 4. Restrict the app to room mailboxes only

An application permission like `Calendars.Read` otherwise grants access to **every** mailbox in
the tenant. Scope it down with an Exchange Online **Application Access Policy** (works on all
current tenants; RBAC for Applications is the newer equivalent where available) restricting this
app to only the room mailboxes it needs:

```powershell
# One mail-enabled security group containing just this tenant's room mailboxes
New-DistributionGroup -Name "OpenRoom Devices" -Type Security `
    -Members room-brighton-1@example.onmicrosoft.com

New-ApplicationAccessPolicy -AppId "<the app registration's Application (client) ID>" `
    -PolicyScopeGroupId "OpenRoom Devices" -AccessRight RestrictAccess `
    -Description "Restrict OpenRoom Graph app to room mailboxes only"
```

**Verify this actually works before rollout** — attempt (from a test script or `Graph Explorer`
using the app's own token) to read a *non-room* mailbox's calendar and confirm it is denied. This
is one of the project's acceptance criteria: "The Graph app cannot read any non-room mailbox
(test and document the result)." Record the result of that test here or in
`docs/OPERATIONS.md` once you've run it against your tenant.

## 5. Conditional Access

Room accounts are shared, unattended, and sign in from one fixed device — the usual per-user MFA
policy doesn't fit and excluding the account from Conditional Access entirely removes a real
control. Prefer a policy scoped to these room accounts that reflects how they actually operate,
for example:

- Grant access only from a trusted **named/network location** (the room's known egress IP or a
  compliant-network requirement), rather than "any location, no MFA".
- Consider a compliant-device or hybrid-joined-device requirement if these devices are enrolled
  in your device management.
- Avoid a blanket MFA exclusion with no compensating control — that trades one risk for a bigger
  one.

Get sign-off from whoever owns Conditional Access policy for the tenant before applying this,
since it affects a real identity in a shared policy surface.

## 6. First sign-in and re-authentication

The room account signs into the Teams web client in the kiosk's Chromium profile (this is
separate from, and unrelated to, the Graph app's certificate auth used for calendar reads):

1. On the device console (not over SSH — it needs the display), stop the kiosk service and start
   a normal Chromium window as the `kiosk` user: see `docs/HARDWARE.md`'s manual test procedure
   for the exact commands.
2. Navigate to `https://teams.microsoft.com`, sign in with the room account's own credentials
   (not the Graph app's certificate), and complete any Conditional Access challenge.
3. Close that Chromium window and restart `openroom-kiosk.service` — the signed-in session
   persists in the `kiosk` user's Chromium profile at `~kiosk/.chromium`.

**Re-authentication**: Teams web sessions eventually expire (token lifetime, a password change,
a Conditional Access policy change, etc.). When that happens the kiosk will show a Microsoft
sign-in prompt instead of the home screen or meeting. Repeat the three steps above to sign back
in. There's no automated re-auth in this build — an operator has to do this manually when it
happens, so document who's on call for it at your site in `docs/OPERATIONS.md`.

## Feeding these values into Ansible

Once you have the tenant ID, app (client) ID, room mailbox UPN, and the certificate/key PEM
files:

```sh
ansible-vault encrypt_string --stdin-name 'graph_client_certificate_pem' < graph-client-cert.pem \
    >> ansible/host_vars/<hostname>.yml
ansible-vault encrypt_string --stdin-name 'graph_client_private_key_pem' < graph-client-key.pem \
    >> ansible/host_vars/<hostname>.yml
```

Then add the non-secret values to the same file in plain text:

```yaml
graph_tenant_id: "<tenant GUID or verified domain>"
graph_client_id: "<app registration's Application (client) ID>"
room_mailbox_upn: "room-brighton-1@example.onmicrosoft.com"
```

Delete the local `graph-client-key.pem`/`graph-client-cert.pem` files once they're encrypted into
`host_vars` — they should not linger on disk outside Ansible Vault. Run the playbook with
`--ask-vault-pass` (or `--vault-password-file`) from then on.
