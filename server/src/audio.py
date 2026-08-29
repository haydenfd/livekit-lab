"""Room audio input configuration."""

from livekit.agents import room_io
from livekit.plugins import ai_coustics


def create_room_options() -> room_io.RoomOptions:
    """Create room options with the existing audio enhancement model."""
    return room_io.RoomOptions(
        audio_input=room_io.AudioInputOptions(
            noise_cancellation=ai_coustics.audio_enhancement(
                model=ai_coustics.EnhancerModel.QUAIL_VF_S
            ),
        ),
    )
