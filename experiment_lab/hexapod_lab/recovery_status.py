"""Read only public-safe recovery progress; never execute a recovery action."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path


_MAX_STATE_BYTES = 16 * 1024
_STATUSES = {"waiting", "attempting", "verifying", "recovered", "needs_attention"}
_ISSUES = {
    "none": "No recoverable failure is currently reported.",
    "lab_unavailable": "The Robot Lab service is not responding.",
    "robot_controller_unavailable": "The robot controller is not providing fresh physical telemetry.",
    "public_lab_unavailable": "The website cannot reach Robot Lab on the Mac.",
    "camera_capture_failed": "The configured robot cameras are not delivering fresh frames.",
    "camera_permission_denied": "macOS is denying camera access to the capture service.",
    "macos_privacy_fd_exhaustion": "The Mac’s privacy service has run out of file handles.",
}
_ACTIONS = {
    "restart_lab": "Restart the Robot Lab service.",
    "restart_camera_tunnel": "Restart the connection from the lab Mac to the website.",
    "restart_user_tccd": "Restart the failed Mac privacy service.",
}
_REASONS = {
    "none": "No automatic repair is currently needed.",
    "hardware_active_or_unobserved": "Waiting until the robot is confirmed idle and no experiment owns the hardware.",
    "disabled": "Automatic recovery is disabled.",
    "confirming_failure": "Checking another fresh observation before attempting a repair.",
    "cooldown": "Waiting for the retry cooldown before another bounded repair attempt.",
    "attempts_exhausted": "The automatic retry limit has been reached.",
    "manual_action_required": "This condition needs a manual fix before automatic recovery can continue.",
    "action_failed": "The last repair action failed; recovery has not been verified.",
    "verification_pending": "Checking fresh status and camera observations after the repair attempt.",
    "observations_stale": "Waiting for fresh observations before deciding whether a repair is safe or complete.",
    "runtime_preflight_failed": "The recovery service could not complete its checks before a repair.",
}


def recovery_status(path: Path, *, now=None) -> dict:
    """Limit file size and publish only enum-derived text and validated values."""
    now = now or datetime.now(timezone.utc)
    result = {
        "status": "unknown", "issue_code": None, "reason_code": None, "event_id": None,
        "headline": "Automatic recovery status is unavailable",
        "summary": "No current recovery report is available.",
        "detail": "Check the recovery monitor on the lab Mac.",
        "action": None, "action_code": None, "attempts": 0,
        "last_attempt_at": None, "verified_at": None, "updated_at": None,
    }
    try:
        with path.open("rb") as source:
            raw = source.read(_MAX_STATE_BYTES + 1)
        if len(raw) > _MAX_STATE_BYTES:
            return result
        state = json.loads(raw)
        if not isinstance(state, dict):
            return result
    except (OSError, ValueError, RecursionError):
        return result

    def known(value, mapping):
        return value if isinstance(value, str) and value in mapping else None

    def timestamp(value):
        if not isinstance(value, str) or len(value) > 64:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed > now + timedelta(seconds=30):
                return None
            return parsed.astimezone(timezone.utc)
        except (ValueError, OverflowError):
            return None

    status = known(state.get("status"), _STATUSES)
    issue = known(state.get("issue_code"), _ISSUES)
    reason = known(state.get("reason_code"), _REASONS)
    action = known(state.get("action"), _ACTIONS)
    if status is None or issue is None:
        return result
    attempts = state.get("attempts")
    attempts = attempts if type(attempts) is int and 0 <= attempts <= 1000 else 0
    event_id = state.get("event_id")
    event_id = event_id if type(event_id) is int and 0 <= event_id <= 2**53 - 1 else None
    attempted = timestamp(state.get("last_attempt_at"))
    verified = timestamp(state.get("verified_at"))
    updated = timestamp(state.get("updated_at"))
    result.update(
        status=status, issue_code=issue, reason_code=reason, event_id=event_id,
        summary=_ISSUES[issue], attempts=attempts,
        action_code=action, action=_ACTIONS.get(action),
        last_attempt_at=attempted.isoformat() if attempted else None,
        verified_at=verified.isoformat() if verified else None,
        updated_at=updated.isoformat() if updated else None,
    )
    if status in {"attempting", "verifying", "waiting"} and (
        updated is None or now - updated > timedelta(minutes=3)
    ):
        result.update(status="unknown", headline="Automatic recovery is not reporting",
                      detail="The recovery monitor has no recent update; current repair activity cannot be confirmed.",
                      action=None, action_code=None)
        return result
    if status == "recovered":
        if verified is None or (attempts and attempted is None) or (attempted and verified < attempted):
            result.update(status="unknown", headline="Recovery has not been verified",
                          detail="The saved report has no valid verification after the latest repair attempt.",
                          action=None, action_code=None, verified_at=None)
        else:
            result.update(headline="Automatic recovery was verified",
                          summary="Earlier failure: " + _ISSUES[issue],
                          detail="Fresh observations confirmed recovery after the reported failure.")
        return result
    if status == "attempting":
        result.update(headline="Automatic recovery is running",
                      detail="A bounded service repair is in progress. Recovery is not yet verified.")
    elif status == "verifying":
        result.update(headline="Checking the recovery result",
                      detail="Checking fresh observations after the repair attempt. Recovery is not yet verified.")
    elif status == "needs_attention":
        result.update(headline="Automatic recovery needs help",
                      detail=_REASONS.get(reason, "The reported failure still needs attention."))
        result["action"] = (
            "On the lab Mac, allow camera access for the capture service, then check for fresh frames."
            if issue == "camera_permission_denied" else
            "Check robot power and its network connection; fresh telemetry is required before service repairs can run."
            if issue == "robot_controller_unavailable" else
            "Inspect the failed service and recovery monitor on the lab Mac before retrying."
        )
        result["action_code"] = None
    else:
        result.update(headline="Automatic recovery is waiting" if issue != "none" else "Automatic recovery is monitoring",
                      detail=_REASONS.get(reason, "The monitor will check again automatically."))
    return result
