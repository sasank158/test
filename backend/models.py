"""
Data models for the Feature Flag & Remote Config Engine.

These models define the "shape" of the data that flows between the
backend, the terminal dashboard (TUI), and any client apps (e.g. Flutter).
"""

from typing import List, Literal, Union
from pydantic import BaseModel, Field


class RolloutRule(BaseModel):
    """
    Describes WHO a feature flag is enabled for.

    type:
        - "everyone"   -> flag applies to all users
        - "beta_only"  -> flag only applies to user IDs in beta_user_ids
        - "percentage" -> flag applies to a consistent percentage of users
    """
    type: Literal["everyone", "beta_only", "percentage"] = "everyone"
    percentage: int = Field(default=100, ge=0, le=100)
    beta_user_ids: List[str] = Field(default_factory=list)


class FeatureFlag(BaseModel):
    """A single on/off feature flag plus its targeting rule."""
    name: str
    enabled: bool = False
    rollout: RolloutRule = Field(default_factory=RolloutRule)


class ConfigValue(BaseModel):
    """A single remote config value (a 'string' or a 'number')."""
    key: str
    # NOTE: `int` is listed before `float` so whole numbers like 5 are
    # serialized to JSON as `5`, not `5.0`.
    value: Union[str, int, float]
    value_type: Literal["string", "number"] = "string"


class AppState(BaseModel):
    """The full state sent to clients: every flag + every config."""
    flags: List[FeatureFlag]
    configs: List[ConfigValue]
