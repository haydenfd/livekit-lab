"""Room audio input configuration."""

from livekit.agents import room_io


def create_room_options() -> room_io.RoomOptions:
    """Create room options without optional paid audio enhancement."""
    return room_io.RoomOptions(
        # Keep the LiveKit room after the agent session ends so post-interview
        # transcript and session state remain inspectable.
        delete_room_on_close=False,
        audio_input=room_io.AudioInputOptions(
            noise_cancellation=None,
        ),
    )
