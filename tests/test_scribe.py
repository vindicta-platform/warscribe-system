import pytest
from uuid import UUID
from datetime import datetime
from warscribe.core.schema.unit import UnitReference
from warscribe.core.schema.action import BaseAction, ActionType
from warscribe.core.schema.transcript import GameTranscript, Player
from vindicta_foundation.models.base import VindictaModel

def test_unit_reference_model():
    unit = UnitReference(name="Intercessors", faction="Space Marines")
    assert isinstance(unit, VindictaModel)
    assert unit.name == "Intercessors"
    assert isinstance(unit.id, UUID)

def test_base_action_model():
    unit = UnitReference(name="Intercessors", faction="Space Marines")
    action = BaseAction(
        action_type=ActionType.MOVE,
        turn=1,
        phase="Movement",
        actor=unit
    )
    assert isinstance(action, VindictaModel)
    assert action.turn == 1
    assert action.actor.name == "Intercessors"

def test_transcript_model():
    p1 = Player(name="Alice", faction="Ultramarines")
    p2 = Player(name="Bob", faction="Necrons")
    
    transcript = GameTranscript(
        player1=p1,
        player2=p2,
        current_turn=1
    )
    
    assert isinstance(transcript, VindictaModel)
    assert transcript.player1.name == "Alice"
    assert transcript.created_at is not None
