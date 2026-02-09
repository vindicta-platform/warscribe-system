"""
Game transcript model for WARScribe.

A transcript is a complete record of a game,
including all actions and metadata.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

from warscribe.core.schema.action import Action
from warscribe.core.schema.unit import UnitReference
from vindicta_foundation.models.base import VindictaModel


class Player(BaseModel):
    """A player in a game."""

    name: str = Field(..., description="Player name")
    faction: str = Field(..., description="Faction played")
    subfaction: Optional[str] = Field(None, description="Subfaction/chapter")

    # Army list (simplified for v0.1.0)
    units: List[UnitReference] = Field(default_factory=list)
    points_total: int = Field(0, ge=0)


class GameTranscript(VindictaModel):
    """
    A complete game transcript.

    Records all actions in chronological order,
    along with game metadata and final results.
    """

    # id, created_at inherited from VindictaModel

    # Game metadata
    edition: str = Field("10th", description="Game edition (10th, 11th)")
    points_limit: int = Field(2000, description="Points limit for the game")
    mission: str = Field("unknown", description="Mission name")
    deployment: str = Field("unknown", description="Deployment type")

    # Players
    player1: Player
    player2: Player

    # Game state
    current_turn: int = Field(1, ge=1)
    active_player: int = Field(1, ge=1, le=2)

    # Actions (chronological)
    actions: list[Action] = Field(default_factory=list)

    # Scoring
    player1_vp: int = Field(0, ge=0)
    player2_vp: int = Field(0, ge=0)

    # Game result
    winner: Optional[int] = Field(
        None, ge=1, le=2, description="1 or 2, None if ongoing"
    )
    conceded: bool = Field(False, description="True if game ended by concession")

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

    # Notes
    notes: Optional[str] = None

    def add_action(self, action: Action) -> None:
        """Add an action to the transcript."""
        self.actions.append(action)

    def get_actions_for_turn(self, turn: int) -> list[Action]:
        """Get all actions for a specific turn."""
        return [a for a in self.actions if a.turn == turn]

    def get_actions_by_unit(self, unit_id: UUID) -> list[Action]:
        """Get all actions by a specific unit."""
        return [a for a in self.actions if a.actor.id == unit_id]

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "GameTranscript":
        """Deserialize from JSON string."""
        return cls.model_validate_json(json_str)
