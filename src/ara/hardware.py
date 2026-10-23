"""Hardware inventory and conservative local-model recommendations."""

from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass

import psutil


@dataclass(frozen=True)
class HardwareInfo:
    """Machine resources relevant to choosing local model sizes."""

    operating_system: str
    architecture: str
    cpu_name: str
    logical_processors: int
    ram_bytes: int | None
    gpu_name: str | None = None
    vram_bytes: int | None = None
    accelerator: str = "cpu"

    @property
    def recommended_model(self) -> str:
        """Return a Qwen instruct model size following the project hardware policy."""
        if self.vram_bytes is not None and self.vram_bytes >= 16 * 1024**3:
            return "qwen2.5:14b"
        if self.vram_bytes is not None and self.vram_bytes >= 6 * 1024**3:
            return "qwen2.5:7b"
        if self.ram_bytes is not None and self.ram_bytes >= 16 * 1024**3:
            return "qwen2.5:3b"
        return "qwen2.5:1.5b"


def detect_hardware() -> HardwareInfo:
    """Inspect CPU, system RAM, and available GPU details without requiring a GPU stack."""
    memory_bytes: int | None
    try:
        memory_bytes = int(psutil.virtual_memory().total)
    except (OSError, AttributeError):
        memory_bytes = None

    gpu_name, vram_bytes = _detect_nvidia_gpu()
    if gpu_name is None:
        gpu_name, vram_bytes = _detect_torch_cuda()
    accelerator = "cuda" if gpu_name else "cpu"
    if gpu_name is None and platform.system() == "Darwin":
        mps_name, mps_vram = _detect_mps()
        if mps_name:
            gpu_name, vram_bytes, accelerator = mps_name, mps_vram, "mps"

    return HardwareInfo(
        operating_system=f"{platform.system()} {platform.release()}",
        architecture=platform.machine() or "unknown",
        cpu_name=platform.processor() or platform.machine() or "unknown",
        logical_processors=os.cpu_count() or 1,
        ram_bytes=memory_bytes,
        gpu_name=gpu_name,
        vram_bytes=vram_bytes,
        accelerator=accelerator,
    )


def _detect_nvidia_gpu() -> tuple[str | None, int | None]:
    """Query NVIDIA driver metadata when `nvidia-smi` is available."""
    executable = shutil.which("nvidia-smi")
    if executable is None:
        return None, None
    try:
        result = subprocess.run(
            [executable, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            check=False,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    if result.returncode != 0 or not result.stdout.strip():
        return None, None
    first_gpu = result.stdout.splitlines()[0].split(",", maxsplit=1)
    if len(first_gpu) != 2:
        return None, None
    try:
        vram_bytes = int(float(first_gpu[1].strip()) * 1024**2)
    except ValueError:
        vram_bytes = None
    return first_gpu[0].strip() or None, vram_bytes


def _detect_mps() -> tuple[str | None, int | None]:
    """Use PyTorch's optional MPS probe when running on macOS with torch installed."""
    if importlib.util.find_spec("torch") is None:
        return None, None
    try:
        import torch

        if torch.backends.mps.is_available():
            return "Apple Metal Performance Shaders", None
    except (ImportError, AttributeError, OSError, RuntimeError):
        return None, None
    return None, None


def _detect_torch_cuda() -> tuple[str | None, int | None]:
    """Use PyTorch's optional CUDA probe if the NVIDIA utility is unavailable."""
    if importlib.util.find_spec("torch") is None:
        return None, None
    try:
        import torch

        if torch.cuda.is_available():
            properties = torch.cuda.get_device_properties(0)
            return properties.name, int(properties.total_memory)
    except (ImportError, AttributeError, OSError, RuntimeError):
        return None, None
    return None, None

