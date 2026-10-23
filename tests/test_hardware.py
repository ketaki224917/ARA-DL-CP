"""Tests for hardware-based model recommendations."""

from ara.hardware import HardwareInfo, detect_hardware


def test_model_recommendation_obeys_vram_and_ram_thresholds() -> None:
    assert HardwareInfo("Linux", "x86_64", "CPU", 8, 8 * 1024**3).recommended_model == (
        "qwen2.5:1.5b"
    )
    assert HardwareInfo("Linux", "x86_64", "CPU", 8, 32 * 1024**3).recommended_model == (
        "qwen2.5:3b"
    )
    midrange = HardwareInfo("Linux", "x86_64", "CPU", 8, 8 * 1024**3, "GPU", 8 * 1024**3)
    high_end = HardwareInfo("Linux", "x86_64", "CPU", 8, None, "GPU", 20 * 1024**3)
    assert midrange.recommended_model == "qwen2.5:7b"
    assert high_end.recommended_model == "qwen2.5:14b"


def test_inventory_returns_cpu_fallback_when_no_nvidia_driver(monkeypatch) -> None:
    monkeypatch.setattr("ara.hardware.shutil.which", lambda _: None)

    info = detect_hardware()

    assert info.logical_processors >= 1
    assert info.accelerator == "cpu"
    assert info.gpu_name is None

