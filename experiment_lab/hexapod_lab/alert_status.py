"""Public-safe status of the separate outage text monitor."""

from datetime import datetime, timezone
import json
from pathlib import Path


def alert_monitor_status(path: Path, *, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            raise ValueError("invalid state")
    except (OSError, ValueError):
        state = {}

    def timestamp(value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else None
        except (AttributeError, TypeError, ValueError):
            return None

    scan = timestamp(state.get("last_scan_at"))
    delivery = state.get("alert_delivery")
    delivery = delivery if isinstance(delivery, dict) else {}
    last_success = timestamp(delivery.get("last_success_at"))
    result = {
        "status": "unverified",
        "headline": "iMessage alerts have not been verified",
        "detail": "The alert monitor has not recorded a successful iMessage submission yet.",
        "action": "Verify the alert monitor and send a test iMessage before relying on outage alerts.",
        "last_scan_at": scan.isoformat() if scan else None,
        "last_success_at": last_success.isoformat() if last_success else None,
    }
    code = delivery.get("error_code")
    if delivery.get("status") == "blocked":
        result.update(status="blocked", headline="iMessage alerts cannot be sent")
        if code == "messages_automation_denied":
            result.update(
                detail="macOS is blocking the alert service from controlling Messages.",
                action="On the Mac, open System Settings → Privacy & Security → Automation and allow the alert application to control Messages. Then send a test iMessage.",
            )
        else:
            result.update(
                detail="The latest iMessage submission failed; the monitor will retry.",
                action="Check Messages and the alert monitor on the Mac, then send a test iMessage.",
            )
    elif last_success:
        result.update(status="ok", headline="iMessage alert submission verified",
                      detail="The monitor has successfully submitted an iMessage through Messages.",
                      action=None)
    if not scan or (now - scan).total_seconds() > 180 or (now - scan).total_seconds() < -30:
        if result["status"] == "blocked":
            result["detail"] += " The monitor also has no recent completed check."
        else:
            result.update(status="stale", headline="iMessage alert monitor is not reporting",
                          detail="No completed monitor check has been recorded in the last three minutes.",
                          action="Check the alert service on the Mac; outage iMessages are not currently verified.")
    return result
