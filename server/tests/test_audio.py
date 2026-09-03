from audio import create_room_options


def test_room_options_do_not_delete_the_room_when_the_session_closes() -> None:
    options = create_room_options()

    assert options.delete_room_on_close is False
    assert options.audio_input.noise_cancellation is None
