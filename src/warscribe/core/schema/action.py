"""
Action models for WARScribe notation.

Core action types per ROADMAP v0.1.0:
- Move
- Shoot
- Charge
- Fight
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Union, List
from uuid import UUID

from pydantic import BaseModel, Field

from warscribe.core.schema.unit import UnitReference
from vindicta_foundation.models.base import VindictaModel


class ActionType(str, Enum):
    """Types of actions that can be recorded."""

    MOVE = "move"
    SHOOT = "shoot"
    CHARGE = "charge"
    FIGHT = "fight"
    ADVANCE = "advance"
    FALL_BACK = "fall_back"
    CONSOLIDATE = "consolidate"
    PILE_IN = "pile_in"
    HEROIC_INTERVENTION = "heroic_intervention"
    STRATAGEM = "stratagem"
    ABILITY = "ability"
    OBJECTIVE = "objective"


class ActionResult(str, Enum):
    """Result of an action."""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    PENDING = "pending"


class BaseAction(VindictaModel):
    """Base class for all actions."""

    # id, created_at inherited from VindictaModel
    action_type: ActionType

    # Timing
    turn: int = Field(..., ge=1, description="Turn number")
    phase: str = Field(..., description="Game phase (e.g., 'movement', 'shooting')")
    # timestamp inherited from VindictaModel (created_at) or specific game time? 
    # VindictaModel has created_at, but actions might have a specific in-game timestamp.
    # We'll keep a specific timestamp field if it represents game time, or map it.
    # WARScribe usually implies "when it happened in real time" which created_at covers.
    # But let's keep 'timestamp' for backward compat if needed, or map it.
    # For now, we'll rely on VindictaModel's created_at, but existing clients might expect 'timestamp'.
    # We can add a property or just keep it as a field if it differs.
    # Let's assume created_at is sufficient for "when recorded", but if we import old logs, we might need a specific field.
    # Re-adding timestamp field explicitly if it serves a distinct domain purpose (e.g. video timestamp).
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Actor
    actor: UnitReference = Field(..., description="The unit performing the action")

    # Result
    result: ActionResult = ActionResult.PENDING

    # Notes
    notes: Optional[str] = Field(None, description="Optional notes about the action")


class RelativeDistance(BaseModel):
    """Distance change relative to another unit.
    
    Sub-component, not a standalone entity, so BaseModel is fine, 
    but VindictaModel gives consistent config. Let's stick to BaseModel for lightweight struct.
    """

    target_unit_id: UUID = Field(..., description="ID of the reference unit")
    target_unit_name: Optional[str] = None
    delta_inches: float = Field(
        ..., description="Change in distance (negative = closer)"
    )
    final_distance: Optional[float] = Field(
        None, ge=0, description="Final distance to target"
    )


class MoveAction(BaseAction):
    """A movement action."""

    action_type: ActionType = ActionType.MOVE

    # Movement details (ALWAYS positive - actual distance moved)
    distance_inches: float = Field(
        ..., ge=0, description="Distance moved in inches (always positive)"
    )
    start_position: Optional[tuple[float, float]] = None
    end_position: Optional[tuple[float, float]] = None

    # Movement modifiers
    is_advance: bool = False
    is_fall_back: bool = False
    terrain_crossed: list[str] = Field(default_factory=list)

    # Relational distances (can be negative = moved closer)
    relative_distances: list[RelativeDistance] = Field(
        default_factory=list,
        description="Distance changes relative to other units (negative = closer)",
    )


class ShootAction(BaseAction):
    """A shooting action."""

    action_type: ActionType = ActionType.SHOOT

    # Target
    target: UnitReference = Field(..., description="Unit being shot at")

    # Weapon info
    weapon_name: str = Field(..., description="Weapon used")
    shots: int = Field(..., ge=1, description="Number of shots")

    # Dice results
    hits: int = Field(0, ge=0)
    wounds: int = Field(0, ge=0)
    saves_failed: int = Field(0, ge=0)
    damage_dealt: int = Field(0, ge=0)
    models_killed: int = Field(0, ge=0)


class ChargeAction(BaseAction):
    """A charge action."""

    action_type: ActionType = ActionType.CHARGE

    # Target(s)
    targets: list[UnitReference] = Field(
        ..., min_length=1, description="Charge targets"
    )

    # Dice
    charge_roll: tuple[int, int] = Field(..., description="2D6 charge roll")
    distance_needed: float = Field(..., ge=0, description="Distance to closest target")

    # Result
    made_charge: bool = False


class FightAction(BaseAction):
    """A fight (melee) action."""

    action_type: ActionType = ActionType.FIGHT

    # Target
    target: UnitReference = Field(..., description="Unit being fought")

    # Weapon info
    weapon_name: str = Field(..., description="Melee weapon used")
    attacks: int = Field(..., ge=1, description="Number of attacks")

    # Dice results
    hits: int = Field(0, ge=0)
    wounds: int = Field(0, ge=0)
    saves_failed: int = Field(0, ge=0)
    damage_dealt: int = Field(0, ge=0)
    models_killed: int = Field(0, ge=0)


# Union type for all actions
Action = Union[MoveAction, ShootAction, ChargeAction, FightAction]
