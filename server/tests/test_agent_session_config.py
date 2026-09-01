from types import SimpleNamespace

from config import agent_session_config


def test_build_agent_session_config_preserves_active_settings(
    monkeypatch,
) -> None:
    turn_detector = object()

    monkeypatch.setattr(
        agent_session_config.deepgram,
        "STT",
        lambda **kwargs: SimpleNamespace(kind="stt", kwargs=kwargs),
    )
    monkeypatch.setattr(
        agent_session_config.openai.responses,
        "LLM",
        lambda **kwargs: SimpleNamespace(kind="llm", kwargs=kwargs),
    )
    monkeypatch.setattr(
        agent_session_config.deepgram,
        "TTS",
        lambda **kwargs: SimpleNamespace(kind="tts", kwargs=kwargs),
    )
    monkeypatch.setattr(
        agent_session_config.inference,
        "TurnDetector",
        lambda: turn_detector,
    )

    config = agent_session_config.build_agent_session_config()

    assert config["stt"].kwargs == {
        "model": "nova-3",
        "language": "en-US",
        "smart_format": True,
    }
    assert config["llm"].kwargs == {"model": "gpt-5.6"}
    assert config["tts"].kwargs == {"model": "aura-2-asteria-en"}
    assert config["expressive"] is False
    assert config["turn_handling"] == {
        "turn_detection": turn_detector,
        "interruption": {
            "enabled": False,
            "discard_audio_if_uninterruptible": True,
        },
        "preemptive_generation": {"enabled": False},
    }


def test_build_agent_session_config_excludes_inactive_tuning_keys(
    monkeypatch,
) -> None:
    monkeypatch.setattr(agent_session_config.deepgram, "STT", lambda **_: object())
    monkeypatch.setattr(agent_session_config.openai.responses, "LLM", lambda **_: object())
    monkeypatch.setattr(agent_session_config.deepgram, "TTS", lambda **_: object())
    monkeypatch.setattr(
        agent_session_config.inference, "TurnDetector", lambda: object()
    )

    config = agent_session_config.build_agent_session_config()
    turn_handling = config["turn_handling"]

    assert "min_consecutive_speech_delay" not in config
    assert "endpointing" not in turn_handling
    assert set(turn_handling["interruption"]) == {
        "enabled",
        "discard_audio_if_uninterruptible",
    }
    assert set(turn_handling["preemptive_generation"]) == {"enabled"}
