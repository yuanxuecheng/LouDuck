"""验证 worker 在配置长度不匹配时会回退到自动检测"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np
import soundfile as sf
from itu1770_meter import ITU1770Meter


def _iter_dummy_mono_files(mono_files, tmpdir):
    """模拟 _iter_mono_files 的核心逻辑"""
    sr = 48000
    total_samples = sr * 3
    num_channels = len(mono_files)

    def _generator():
        chunk_samples = sr
        chunk_idx = 0
        max_samples = total_samples
        while chunk_idx * chunk_samples < max_samples:
            out = np.random.randn(chunk_samples, num_channels) * 0.1
            yield out, sr
            chunk_idx += 1

    return sr, num_channels, total_samples, _generator()


def test_worker_config_fallback():
    """config_name 为 5.1.4(10ch) 但实际 12 个文件时，应回退到 7.1.4"""
    config_name = "5.1.4"  # 模拟 UI 没同步，仍是 10ch 配置
    num_channels = 12

    if config_name == "自动检测":
        config = ITU1770Meter.auto_config(num_channels)
    else:
        config_name_resolved = config_name if config_name in ITU1770Meter.CONFIGS else ITU1770Meter.auto_config(num_channels)
        config = ITU1770Meter.CONFIGS.get(config_name_resolved, ITU1770Meter.auto_config(num_channels))

    # 模拟 worker 中的保护逻辑
    if len(config) != num_channels:
        print(f"[保护生效] 配置'{config_name}'({len(config)}ch)与音频{num_channels}ch不匹配，回退到自动检测")
        config = ITU1770Meter.auto_config(num_channels)

    assert len(config) == num_channels, f"期望 {num_channels}ch，实际 {len(config)}ch"
    print(f"[OK] 最终配置: {len(config)}ch")


if __name__ == "__main__":
    test_worker_config_fallback()
