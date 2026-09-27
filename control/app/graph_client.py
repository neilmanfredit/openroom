from typing import Optional

import httpx
import msal


class GraphAuthError(Exception):
    pass


class GraphCalendarClient:
    """Reads the room mailbox's calendar view via Microsoft Graph, using
    the client-credentials flow with certificate auth (no client secret —
    see docs/M365-SETUP.md). The app registration is restricted to this
    one room mailbox via Exchange Online RBAC/an Application Access
    Policy, documented (not automated) there too.
    """

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        certificate_pem: str,
        private_key_pem: str,
        room_mailbox_upn: str,
        timezone: str = "Europe/London",
    ):
        self._room_mailbox_upn = room_mailbox_upn
        self._timezone = timezone
        # No explicit "thumbprint" here: that's msal's older SHA-1 path,
        # kept only for ADFS compatibility. Omitting it and supplying
        # public_certificate lets msal (>=1.35) derive a SHA-256
        # thumbprint itself.
        self._msal_app = msal.ConfidentialClientApplication(
            client_id=client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential={
                "private_key": private_key_pem,
                "public_certificate": certificate_pem,
            },
        )

    def _access_token(self) -> str:
        result = self._msal_app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" not in result:
            raise GraphAuthError(result.get("error_description", "token acquisition failed"))
        return result["access_token"]

    def fetch_today_events(self, start_iso: str, end_iso: str) -> list[dict]:
        # msal/requests are synchronous; callers run this in a worker
        # thread (see calendar.py) so it doesn't block the event loop.
        token = self._access_token()
        url = f"{self.GRAPH_BASE}/users/{self._room_mailbox_upn}/calendarView"
        headers = {
            "Authorization": f"Bearer {token}",
            "Prefer": f'outlook.timezone="{self._timezone}"',
        }
        params = {
            "startDateTime": start_iso,
            "endDateTime": end_iso,
            "$select": "id,subject,organizer,start,end,onlineMeeting,body,sensitivity",
            "$orderby": "start/dateTime",
        }
        with httpx.Client() as client:
            resp = client.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json().get("value", [])


def build_graph_client(settings) -> Optional[GraphCalendarClient]:
    """Returns None (calendar polling disabled) rather than raising when
    the room's Graph app registration hasn't been set up yet — a device
    should still boot to a working (if calendar-less) home screen."""
    if not (settings.graph_tenant_id and settings.graph_client_id and settings.room_mailbox_upn):
        return None
    try:
        certificate_pem = open(settings.graph_cert_path).read()
        private_key_pem = open(settings.graph_key_path).read()
    except OSError:
        return None
    return GraphCalendarClient(
        tenant_id=settings.graph_tenant_id,
        client_id=settings.graph_client_id,
        certificate_pem=certificate_pem,
        private_key_pem=private_key_pem,
        room_mailbox_upn=settings.room_mailbox_upn,
        timezone=settings.calendar_timezone,
    )
