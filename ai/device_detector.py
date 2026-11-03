import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional


@dataclass
class HardwareProfile:
    device: str
    compute_type: str
    cpu_threads: int
    recommended_model: str
    description: str
    has_vulkan_gpu: bool
    gpu_name: str


class DeviceDetector:
    """Detecta el hardware del sistema y determina la configuración óptima para Whisper."""

    _cached_gpu_name: Optional[str] = None

    @classmethod
    def get_gpu_name(cls) -> str:
        if cls._cached_gpu_name is not None:
            return cls._cached_gpu_name

        name = "GPU Dedicada"
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name | Select-Object -First 1",
            ]
            detected = subprocess.check_output(cmd, text=True, timeout=2).strip()
            if detected:
                name = detected
        except Exception:
            pass

        cls._cached_gpu_name = name
        return name

    @classmethod
    def get_profile(cls) -> HardwareProfile:
        cpu_count = os.cpu_count() or 4
        whisper_threads = max(2, min(cpu_count - 2, 8))

        # Comprobar si whisper-cli Vulkan está presente
        project_root = Path(__file__).resolve().parent.parent
        vulkan_cli = project_root / "bin" / "vulkan" / "whisper-cli.exe"
        has_vulkan = vulkan_cli.exists()

        raw_gpu = cls.get_gpu_name() if has_vulkan else "No configurada"
        gpu_name = f"{raw_gpu} (Aceleración Vulkan activa)" if has_vulkan else "No configurada"

        return HardwareProfile(
            device="cpu",
            compute_type="int8",
            cpu_threads=whisper_threads,
            recommended_model="medium",
            description=f"CPU Multinúcleo ({cpu_count} hilos detectados, {whisper_threads} asignados con INT8)",
            has_vulkan_gpu=has_vulkan,
            gpu_name=gpu_name,
        )

    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        profile = cls.get_profile()
        return {
            "device": profile.device,
            "compute_type": profile.compute_type,
            "threads": profile.cpu_threads,
            "recommended_model": profile.recommended_model,
            "description": profile.description,
            "has_vulkan_gpu": profile.has_vulkan_gpu,
            "gpu_name": profile.gpu_name,
        }
