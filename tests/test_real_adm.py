"""用真实 ADM 文件验证直接测量路径不再越界"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import soundfile as sf
from adm_parser import BW64Parser
from itu1770_meter import ITU1770Meter


def test_real_adm_direct_measure():
    adm_path = PROJECT_ROOT / "0414 Logic 2 空间音频 ADM.wav"
    if not adm_path.exists():
        print(f"跳过测试: 未找到 {adm_path}")
        return

    parser = BW64Parser(str(adm_path))
    adm = parser.parse()

    info = sf.info(str(adm_path))
    sr = info.samplerate
    num_channels = info.channels
    total_samples = info.frames
    print(f"ADM 文件: {num_channels}ch, {sr}Hz, {total_samples} samples")

    config = adm.to_itu1770_config(num_channels)
    print(f"ADM config 长度: {len(config)}")
    assert len(config) == num_channels, "配置长度应与音频通道数一致"

    meter = ITU1770Meter(config, sr)
    meter.reset(sr)

    processed = 0
    max_samples = sr * 5  # 只测前 5 秒
    for chunk, _sr in parser.iter_audio_blocks(block_samples=sr, dtype='float32'):
        if chunk.ndim == 1:
            chunk = chunk.reshape(-1, 1)
        meter.feed(chunk)
        processed += chunk.shape[0]
        if processed >= max_samples:
            break

    result = meter.finalize()
    print(f"测量完成: integrated={result['integrated']:.2f} LKFS, "
          f"true_peak={result['true_peak']:.2f} dBTP, lra={result['lra']:.2f} LU")


if __name__ == "__main__":
    test_real_adm_direct_measure()
