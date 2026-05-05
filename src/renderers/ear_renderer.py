"""
EBU ADM Renderer (EAR) 包装层
支持 Dolby Atmos 和 Audio Vivid (ADM 格式) 渲染到标准扬声器布局

依赖: pip install ear
注意: Python 3.14 + setuptools 82+ 需要手动 patch pkg_resources -> importlib.resources
"""

import re
import struct
import tempfile
from pathlib import Path
from typing import Optional, List

from ear.cmdline.render_file import OfflineRenderDriver
from ear.core.bs2051 import layout_names, get_layout
from ear.fileio import openBw64


# 友好名称 -> EAR 系统名称 (ITU-R BS.2051)
LAYOUT_MAP = {
    "Stereo (2.0)": "0+2+0",
    "5.1 (6ch)": "0+5+0",
    "7.1 (8ch)": "0+7+0",
    "5.1.4 (10ch)": "4+5+0",
    "7.1.4 (12ch)": "4+7+0",
    "9.1.6 (16ch)": "4+9+0",
    "22.2 (24ch)": "9+10+3",
}

# 用于修复 Pro Tools / Dolby Atmos ADM 中 audioStreamFormat 的双重引用
_AUDIOSTREAM_RE = re.compile(
    r'(<audioStreamFormat\b[^>]*>)(.*?)(</audioStreamFormat>)',
    re.DOTALL
)


def _fix_adm_xml(axml_data: bytes) -> bytes:
    """
    修复 ADM XML：
    1. 移除 audioStreamFormat 中同时存在的 audioPackFormatIDRef。
    2. 将 Room-Centric 风格的 LFE speakerLabel 映射为标准 ITU 标签 LFE1，
       确保 EAR 正确识别并路由到目标布局的 LFE 声道。
    """
    xml_str = axml_data.decode('utf-8')

    def _fix_stream_block(m):
        open_tag = m.group(1)
        body = m.group(2)
        close_tag = m.group(3)
        has_channel = '<audioChannelFormatIDRef>' in body
        has_pack = '<audioPackFormatIDRef>' in body
        if has_channel and has_pack:
            body = re.sub(
                r'\s*<audioPackFormatIDRef>[^<]+</audioPackFormatIDRef>\s*',
                '',
                body,
            )
        return open_tag + body + close_tag

    xml_str = _AUDIOSTREAM_RE.sub(_fix_stream_block, xml_str)

    # 修复 Room-Centric LFE speakerLabel：RC_LFE / RoomCentricLFE 等 → LFE1
    xml_str = re.sub(
        r'(<speakerLabel>)(RC_LFE|RoomCentricLFE|LFE_RoomCentric)(</speakerLabel>)',
        r'\1LFE1\3',
        xml_str,
    )

    return xml_str.encode('utf-8')


def _create_fixed_bw64(input_path: str) -> str:
    """
    复制 BW64/RIFF 文件，修复 axml chunk 中的 audioStreamFormat 双重引用。
    返回临时文件路径。
    """
    with open(input_path, 'rb') as f:
        data = bytearray(f.read())

    # 遍历 RIFF chunk 找到 axml
    pos = 12  # 跳过 12 字节 BW64/RIFF header
    axml_data_pos = None
    axml_data_size = None

    while pos < len(data):
        chunk_id = data[pos:pos + 4]
        if len(chunk_id) < 4:
            break
        chunk_size = struct.unpack('<I', data[pos + 4:pos + 8])[0]

        if chunk_id == b'axml':
            axml_data_pos = pos + 8
            axml_data_size = chunk_size
            break

        pos += 8 + chunk_size + (chunk_size % 2)

    if axml_data_pos is None:
        raise ValueError("文件不包含 axml chunk")

    axml_data = bytes(data[axml_data_pos:axml_data_pos + axml_data_size])
    fixed_xml = _fix_adm_xml(axml_data)

    old_padded = axml_data_size + (axml_data_size % 2)
    new_padded = len(fixed_xml) + (len(fixed_xml) % 2)

    new_data = bytearray()
    new_data.extend(data[:axml_data_pos])          # header + axml chunk header
    new_data.extend(fixed_xml)
    if len(fixed_xml) % 2:
        new_data.append(0)
    new_data.extend(data[axml_data_pos + old_padded:])  # 剩余部分

    # 更新 axml chunk size
    struct.pack_into('<I', new_data, axml_data_pos - 4, len(fixed_xml))
    # 更新文件总大小（从 WAVE 之后算起）
    struct.pack_into('<I', new_data, 4, len(new_data) - 8)

    temp_path = str(
        Path(tempfile.gettempdir()) / f"fixed_{Path(input_path).name}"
    )
    with open(temp_path, 'wb') as f:
        f.write(new_data)

    return temp_path


def get_supported_layouts() -> List[str]:
    """获取支持的渲染目标布局列表"""
    return list(LAYOUT_MAP.keys())


def is_object_based_adm(filepath: str) -> bool:
    """检查 ADM 文件是否包含基于对象的音频（如 Dolby Atmos / Audio Vivid）"""
    # 优先使用 EAR 原生解析
    try:
        from ear.fileio import openBw64Adm
        with openBw64Adm(filepath) as infile:
            adm = infile.adm
            if adm is not None:
                objects = getattr(adm, "audio_objects", [])
                if len(objects) > 0:
                    return True
    except Exception:
        pass

    # 后备：使用 adm_parser 检测（避免 EAR Python 3.14 兼容性问题）
    try:
        import sys
        from pathlib import Path
        src_dir = str(Path(__file__).parent.parent)
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        from adm_parser import BW64Parser
        adm = BW64Parser(filepath).parse()
        if adm:
            objects_ch = [ch for ch in adm.channel_formats if ch.type == 'Objects']
            return len(objects_ch) > 0
    except Exception:
        pass

    return False


def get_adm_info(filepath: str) -> dict:
    """获取 ADM 文件的基本信息"""
    try:
        from ear.fileio import openBw64Adm
        with openBw64Adm(filepath) as infile:
            adm = infile.adm
            if adm is None:
                return {"error": "文件不包含有效的 ADM 元数据"}
            objects = getattr(adm, "audio_objects", [])
            beds = [
                o for o in objects
                if not hasattr(o, "audio_object_interaction") or o.audio_object_interaction is None
            ]
            return {
                "programmes": len(getattr(adm, "audio_programmes", [])),
                "objects": len(objects),
                "beds": len(beds),
                "sample_rate": getattr(infile, "sampleRate", 48000),
                "channels": getattr(infile, "channels", 0),
                "duration": getattr(infile, "duration", 0.0),
                "is_object_based": len(objects) > 0,
            }
    except Exception as e:
        msg = str(e)
        if "audioIDs" in msg or "adm" in msg.lower() or "NoneType" in msg:
            return {"error": "文件不包含有效的 ADM 元数据"}
        return {"error": msg}


def render_adm(
    input_path: str,
    target_layout: str,
    output_path: Optional[str] = None,
) -> str:
    """
    渲染 ADM 文件到指定声道布局

    Args:
        input_path: ADM/BW64 文件路径
        target_layout: 友好名称，如 "5.1.4 (10ch)"
        output_path: 输出 WAV 路径，None 则创建临时文件

    Returns:
        输出 WAV 文件路径

    Raises:
        ValueError: 不支持的目标布局
        Exception: 渲染过程中出错（文件不是有效 ADM、解码失败等）
    """
    ear_system = LAYOUT_MAP.get(target_layout)
    if not ear_system:
        raise ValueError(
            f"不支持的目标布局: {target_layout}。支持: {list(LAYOUT_MAP.keys())}"
        )

    if output_path is None:
        output_path = str(
            Path(tempfile.gettempdir()) / f"{Path(input_path).stem}_rndrd.wav"
        )

    driver = OfflineRenderDriver(
        target_layout=ear_system,
        speakers_file=None,
        output_gain_db=0,
        fail_on_overload=False,
        enable_block_duration_fix=True,
    )

    # 策略 B：先尝试原始文件；若因 audioStreamFormat 双重引用失败，自动修复并重试
    try:
        driver.run(input_path, output_path)
        return output_path
    except Exception as first_err:
        err_msg = str(first_err)
        if "has a reference to both" in err_msg:
            fixed_path = _create_fixed_bw64(input_path)
            try:
                driver.run(fixed_path, output_path)
                return output_path
            finally:
                try:
                    import os
                    os.remove(fixed_path)
                except Exception:
                    pass
        else:
            raise
