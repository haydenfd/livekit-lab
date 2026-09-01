"""Room audio input configuration."""

from livekit.agents import room_io
from livekit.plugins import ai_coustics


def create_room_options() -> room_io.RoomOptions:
    """Create room options with the existing audio enhancement model."""
    return room_io.RoomOptions(
        # End the browser call along with the agent session after the closing line.
        delete_room_on_close=True,
        audio_input=room_io.AudioInputOptions(
            noise_cancellation=ai_coustics.audio_enhancement(
                model=ai_coustics.EnhancerModel.QUAIL_VF_S
            ),
        ),
    )
