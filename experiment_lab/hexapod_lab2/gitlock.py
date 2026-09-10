"""One lock for every git operation on the runner checkout.

The builder, the engineer and the loop's sync all fetch into the same
repository from different threads. Two fetches at once produce "cannot lock
ref refs/remotes/origin/main" (seen 2026-09-10 2:30 PM) and a torn
FETCH_HEAD. Take this lock around any git call that touches the checkout.
"""
import threading

GIT_LOCK = threading.RLock()
