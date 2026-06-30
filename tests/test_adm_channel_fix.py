"""验证 ADM 声道配置长度修复"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np
from adm_parser import ADM, ADMChannel
from itu1770_meter import ITU1770Meter


def test_to_itu1770_config_pad():
    """ADM 只有 DirectSpeakers 时，补齐到实际通道数"""
    adm = ADM(axml_data=b"")
    # 模拟 10 个 DirectSpeakers
    adm.channel_formats = [
        ADMChannel(id=f"CH_{i}", name=f"Ch{i}", type="DirectSpeakers",
                   position={"azimuth": 30, "elevation": 0}, is_lfe=False)
        for i in range(10)
    ]

    # 实际文件有 14 个通道
    config = adm.to_itu1770_config(num_channels=14)
    assert len(config) == 14, f"期望 14 个配置，实际 {len(config)}"
    print(f"[OK] 补齐后配置数: {len(config)}")


def test_to_itu1770_config_truncate():
    """DirectSpeakers 多于实际通道数时截断"""
    adm = ADM(axml_data=b"")
    adm.channel_formats = [
        ADMChannel(id=f"CH_{i}", name=f"Ch{i}", type="DirectSpeakers",
                   position={"azimuth": 30, "elevation": 0}, is_lfe=False)
        for i in range(10)
    ]

    config = adm.to_itu1770_config(num_channels=6)
    assert len(config) == 6, f"期望 6 个配置，实际 {len(config)}"
    print(f"[OK] 截断后配置数: {len(config)}")


def test_meter_feed_channel_mismatch():
    """meter 配置长度与 chunk 通道数不一致时抛出明确错误"""
    config = ITU1770Meter.auto_config(2)  # stereo
    meter = ITU1770Meter(config, 48000)
    meter.reset(48000)

    chunk_4ch = np.random.randn(4800, 4)
    try:
        meter.feed(chunk_4ch)
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        assert "通道数不匹配" in str(e), f"错误信息不符: {e}"
        print(f"[OK] 通道不匹配时正确报错: {e}")
    del meter  # 避免状态影响后续测试


def test_meter_feed_ok():
    """配置与 chunk 通道数一致时正常处理"""
    config = ITU1770Meter.auto_config(6)  # 5.1
    meter = ITU1770Meter(config, 48000)
    meter.reset(48000)

    chunk_6ch = np.random.randn(48000 * 5, 6) * 0.1
    meter.feed(chunk_6ch)  # 不应报错
    result = meter.finalize()
    assert result["integrated"] > -100
    print(f"[OK] 6ch 正常测量，integrated={result['integrated']:.2f} LKFS")


if __name__ == "__main__":
    test_to_itu1770_config_pad()
    test_to_itu1770_config_truncate()
    test_meter_feed_channel_mismatch()
    test_meter_feed_ok()
    print("\n全部通过")
