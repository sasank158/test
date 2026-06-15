"""
Flag evaluation logic.

This is the "brain" that decides, for a given user, whether a feature
flag is ON or OFF. The SAME algorithm is re-implemented in the Flutter
client (see flutter_client/feature_flag_client/lib/src/models.dart) so
that a user lands in the same bucket whether the decision is made on the
server or on the device.
"""

import hashlib
from typing import Optional

from models import FeatureFlag


def is_flag_enabled(flag: FeatureFlag, user_id: Optional[str] = None) -> bool:
    """Return True if `flag` should be ON for `user_id`."""
    if not flag.enabled:
        return False

    rollout = flag.rollout

    if rollout.type == "everyone":
        return True

    if rollout.type == "beta_only":
        return user_id is not None and user_id in rollout.beta_user_ids

    if rollout.type == "percentage":
        if user_id is None:
            return False
        return bucket_for_user(flag.name, user_id) < rollout.percentage

    return False


def bucket_for_user(flag_name: str, user_id: str) -> int:
    """
    Deterministically map a (flag_name, user_id) pair to a number 0-99.

    Because this is a pure function of the inputs, the SAME user always
    lands in the SAME bucket for the SAME flag — so a 10% rollout always
    includes/excludes the same people, even across restarts.
    """
    digest = hashlib.md5(f"{flag_name}:{user_id}".encode("utf-8")).hexdigest()
    return int(digest, 16) % 100
