"""
Unit reference model for WARScribe notation.

Provides a way to reference units on the battlefield
without duplicating full unit data.
"""

from typing import Optional

from pydantic import Field
from vindicta_foundation.models.base import VindictaModel


class UnitReference(VindictaModel):
    """
    A reference to a unit in a game.

    Used in actions to identify which unit is acting or being targeted.
    Can include optional extra context like remaining wounds/models.
    """

    # id is inherited from VindictaModel
    name: str = Field(..., description="Unit name (e.g., 'Intercessor Squad A')")
    faction: str = Field(..., description="Faction name")

    # Optional context (filled in when relevant)
    wounds_remaining: Optional[int] = Field(None, description="Current wounds")
    models_remaining: Optional[int] = Field(None, description="Current models")

    # Position (optional, for spatial tracking)
    position_x: Optional[float] = Field(None, description="X coordinate")
    position_y: Optional[float] = Field(None, description="Y coordinate")

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"{self.name} ({self.faction})"

    def short_ref(self) -> str:
        """Short reference string for compact notation."""
        return f"{self.name[:10]}..."[:12] if len(self.name) > 12 else self.name
