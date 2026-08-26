"""
EBU ADM Renderer (EAR) 包装层
支持 Dolby Atmos 和 Audio Vivid (ADM 格式) 渲染到标准扬声器布局

依赖: pip install ear
注意: Python 3.14 + setuptools 82+ 需要手动 patch pkg_resources -> importlib.resources
"""

import re
import struct
import tempfile
import warnings
from pathlib import Path
from typing import Optional, List

# 抑制 EAR 在修正 ADM blockFormat timing 时产生的大量 UserWarning，避免 terminal 被刷屏
warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="ear.fileio.adm.timing_fixes",
)

import numpy as np

# 修复 macOS Apple Silicon 上 numpy.linalg.inv 因输入数组非 C-contiguous
# 或内存布局问题触发 SIGBUS / bus error 的问题（EAR 的 point_source.Triplet
# 在初始化时会调用 np.linalg.inv(self.positions)）。
_original_linalg_inv = np.linalg.inv


def _safe_linalg_inv(a):
    """包装 np.linalg.inv，确保输入为 C-contiguous float64 数组。"""
    arr = np.asarray(a)
    if arr.ndim == 2 and arr.shape[0] == arr.shape[1]:
        arr = np.ascontiguousarray(arr, dtype=np.float64)
    return _original_linalg_inv(arr)


np.linalg.inv = _safe_linalg_inv

from ear.cmdline.render_file import OfflineRenderDriver, PeakMonitor
from ear.core.bs2051 import layout_names, get_layout
from ear.fileio import openBw64, openBw64Adm
from ear.fileio.bw64.chunks import FormatInfoChunk
from ear.fileio.adm import timing_fixes


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


def _create_fixed_bw64(input_path: str, progress_callback=None) -> str:
    """
    复制 BW64/RIFF/RF64 文件，修复 axml chunk 中的 audioStreamFormat 双重引用。

    关键点：
    - 不一次性把整个文件读入内存，使用流式 I/O，支持 >4GB 的大文件。
    - 支持 BW64/RF64 格式和 ds64 chunk，正确识别 0xFFFFFFFF 的 64 位 data chunk。
    - 保留原文件中的 fmt、chna 以及其他辅助 chunk，只替换 axml。
    - 流式复制音频数据并可选调用 progress_callback(0-100)。

    返回临时文件路径。
    """
    input_path = Path(input_path)
    temp_path = Path(tempfile.gettempdir()) / f"fixed_{input_path.name}"
    file_size = input_path.stat().st_size

    # ---------------- 阶段 1：扫描所有 chunk，记录位置与大小 ----------------
    chunks = []
    ds64_info = None
    is_rf64 = False

    with open(input_path, 'rb') as src:
        header = src.read(12)
        if len(header) < 12:
            raise ValueError("文件头不完整")

        riff_id = header[0:4]
        file_size_32 = struct.unpack('<I', header[4:8])[0]
        wave_id = header[8:12]

        if riff_id not in (b'RIFF', b'BW64', b'RF64'):
            raise ValueError(f"不是有效的 RIFF/BW64/RF64 文件: {riff_id!r}")
        if wave_id not in (b'WAVE', b'BW64'):
            raise ValueError(f"不是有效的 WAVE/BW64 格式: {wave_id!r}")

        is_rf64 = (riff_id in (b'BW64', b'RF64')) or (file_size_32 == 0xFFFFFFFF)

        pos = 12
        while pos < file_size:
            src.seek(pos)
            chunk_id = src.read(4)
            if len(chunk_id) < 4:
                break

            chunk_size_bytes = src.read(4)
            if len(chunk_size_bytes) < 4:
                break
            chunk_size = struct.unpack('<I', chunk_size_bytes)[0]
            chunk_data_pos = pos + 8

            # 用于后续计算位置的真实大小；64 位占位符会在下面替换
            real_chunk_size = chunk_size

            if chunk_id == b'ds64':
                try:
                    riff_size_64 = struct.unpack('<Q', src.read(8))[0]
                    data_size_64 = struct.unpack('<Q', src.read(8))[0]
                    sample_count_64 = struct.unpack('<Q', src.read(8))[0]
                    table_length = struct.unpack('<I', src.read(4))[0]
                except struct.error as e:
                    raise ValueError(f"ds64 chunk 格式错误: {e}")
                ds64_info = {
                    'riff_size': riff_size_64,
                    'data_size': data_size_64,
                    'sample_count': sample_count_64,
                    'table_length': table_length,
                }

            # RF64/BW64 大文件的 data chunk 可能用 0xFFFFFFFF 占位，
            # 真实大小存储在 ds64 chunk 中。必须正确跳过数据块，
            # 否则后续（如 data 之后的 axml）会被漏扫。
            if chunk_id == b'data' and chunk_size == 0xFFFFFFFF:
                if ds64_info is None:
                    raise ValueError("64 位 data chunk 缺少 ds64 信息")
                real_chunk_size = ds64_info['data_size']
                print(f"[EAR修复] 64 位 data chunk，使用 ds64 data_size: {real_chunk_size}")

            chunks.append({
                'id': chunk_id,
                'pos': pos,
                'size': chunk_size,
                'data_pos': chunk_data_pos,
                'real_size': real_chunk_size,
            })

            padded_size = real_chunk_size + (real_chunk_size % 2)
            next_pos = chunk_data_pos + padded_size
            if next_pos <= pos:
                # 防止病态的 0xFFFFFFFF 导致死循环；安全退出
                print(f"[EAR修复] 警告: chunk {chunk_id!r} 导致位置未前进，停止扫描")
                break
            pos = next_pos

    axml_chunk = next((c for c in chunks if c['id'] == b'axml'), None)
    if axml_chunk is None:
        raise ValueError("文件不包含 axml chunk")

    data_chunk = next((c for c in chunks if c['id'] == b'data'), None)
    if data_chunk is None:
        raise ValueError("文件不包含 data chunk")

    print(f"[EAR修复] 扫描完成: {len(chunks)} 个 chunk, axml 大小={axml_chunk['size']}, "
          f"data 大小声明={data_chunk['size']}, data 实际大小={data_chunk['real_size']}")

    # ---------------- 阶段 2：读取并修复 axml ----------------
    with open(input_path, 'rb') as src:
        src.seek(axml_chunk['data_pos'])
        axml_data = src.read(axml_chunk['size'])

    fixed_xml = _fix_adm_xml(axml_data)
    new_axml_size = len(fixed_xml)
    new_axml_padded = new_axml_size + (new_axml_size % 2)
    old_axml_padded = axml_chunk['size'] + (axml_chunk['size'] % 2)

    # ---------------- 阶段 3：计算 data 实际大小与新文件总大小 ----------------
    actual_data_size = data_chunk['real_size']

    # 新文件从 'WAVE' 之后到文件末尾的大小（RIFF size 字段含义）
    new_riff_size = 4  # 'WAVE'
    for c in chunks:
        if c['id'] == b'axml':
            new_riff_size += 8 + new_axml_padded
        elif c['id'] == b'data':
            new_riff_size += 8 + actual_data_size + (actual_data_size % 2)
        else:
            new_riff_size += 8 + c['real_size'] + (c['real_size'] % 2)

    use_rf64 = is_rf64 or (new_riff_size > 0xFFFFFFF0)

    print(f"[EAR修复] 原文件 RF64={is_rf64}, 新文件总 riff_size={new_riff_size}, "
          f"使用 RF64={use_rf64}, 音频数据大小={actual_data_size}")

    # ---------------- 阶段 4：流式构建新文件 ----------------
    COPY_BUF = 1024 * 1024  # 1 MB

    def _copy_stream(src, dst, offset: int, size: int, callback=None, total=None):
        """从 src 的 offset 处流式复制 size 字节到 dst，可选汇报进度。"""
        src.seek(offset)
        remaining = size
        copied = 0
        while remaining > 0:
            to_read = min(COPY_BUF, remaining)
            buf = src.read(to_read)
            if not buf:
                break
            dst.write(buf)
            copied += len(buf)
            remaining -= len(buf)
            if callback and total and total > 0:
                callback(min(100, int(copied / total * 100)))

    with open(input_path, 'rb') as src, open(temp_path, 'wb') as dst:
        # 写入 RIFF/RF64 header
        if use_rf64:
            dst.write(b'RF64')
            dst.write(struct.pack('<I', 0xFFFFFFFF))
            dst.write(b'WAVE')
        else:
            if new_riff_size > 0xFFFFFFFF:
                raise ValueError("文件大小超过 RIFF 32 位限制但未启用 RF64")
            dst.write(b'RIFF')
            dst.write(struct.pack('<I', new_riff_size))
            dst.write(b'WAVE')

        for c in chunks:
            cid = c['id']

            if cid == b'axml':
                # 写入修复后的 axml
                dst.write(b'axml')
                dst.write(struct.pack('<I', new_axml_size))
                dst.write(fixed_xml)
                if new_axml_size % 2:
                    dst.write(b'\x00')

            elif cid == b'ds64':
                # 重写 ds64 以匹配新文件大小
                dst.write(b'ds64')
                # 最小 ds64: 3*uint64 + 1*uint32 = 24 + 4 = 28 bytes
                dst.write(struct.pack('<I', 28))
                dst.write(struct.pack('<Q', new_riff_size))
                dst.write(struct.pack('<Q', actual_data_size))
                dst.write(struct.pack('<Q', ds64_info['sample_count'] if ds64_info else 0))
                dst.write(struct.pack('<I', 0))  # tableLength

            elif cid == b'data':
                # 写入 data chunk header
                dst.write(b'data')
                if use_rf64:
                    dst.write(struct.pack('<I', 0xFFFFFFFF))
                else:
                    dst.write(struct.pack('<I', actual_data_size))

                # 流式复制音频数据，期间汇报进度
                if progress_callback:
                    # 修复阶段从 0% 到 100%
                    _copy_stream(
                        src, dst, c['data_pos'], actual_data_size,
                        callback=progress_callback, total=actual_data_size,
                    )
                else:
                    _copy_stream(src, dst, c['data_pos'], actual_data_size)

                if actual_data_size % 2:
                    dst.write(b'\x00')

            else:
                # 原样复制其他 chunk（使用 real_size 跳过可能存在的 64 位占位）
                dst.write(cid)
                dst.write(struct.pack('<I', c['size']))
                _copy_stream(src, dst, c['data_pos'], c['real_size'])
                if c['real_size'] % 2:
                    dst.write(b'\x00')

    print(f"[EAR修复] 已生成修复文件: {temp_path} ({temp_path.stat().st_size} bytes)")
    return str(temp_path)


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
        _ensure_soundfile_compatible(output_path)
        return output_path
    except Exception as first_err:
        err_msg = str(first_err)
        if "has a reference to both" in err_msg:
            fixed_path = _create_fixed_bw64(input_path)
            try:
                driver.run(fixed_path, output_path)
                _ensure_soundfile_compatible(output_path)
                return output_path
            finally:
                try:
                    import os
                    os.remove(fixed_path)
                except Exception:
                    pass
        else:
            raise


def _ensure_soundfile_compatible(path: str) -> None:
    """
    EAR 的 Bw64Writer 在大文件（>=4GB）时会把文件头写成 BW64 格式。
    libsndfile/soundfile 原生不支持 BW64，但支持结构几乎相同的 RF64。
    此函数在渲染完成后把纯 PCM 输出文件的 BW64 头就地改写为 RF64，使其
    能被后续 soundfile 读取与测量。

    仅修改文件头前 4 个字节，不触碰任何 chunk 内容；对普通 RIFF/WAV
    文件没有任何影响。
    """
    try:
        with open(path, 'r+b') as f:
            header = f.read(4)
            if header == b'BW64':
                f.seek(0)
                f.write(b'RF64')
                print(f"[EAR渲染] 大文件输出头从 BW64 改写为 RF64: {path}")
            elif header == b'RIFF':
                print(f"[EAR渲染] 输出为普通 RIFF/WAV，无需改写: {path}")
    except Exception as e:
        print(f"[EAR渲染] 警告: 检查/改写输出文件头失败: {e}")


def render_adm_with_progress(
    input_path: str,
    target_layout: str,
    output_path: Optional[str] = None,
    progress_callback=None,
) -> str:
    """
    渲染 ADM 文件到指定声道布局，支持进度回调。

    Args:
        input_path: ADM/BW64 文件路径
        target_layout: 友好名称，如 "5.1.4 (10ch)"
        output_path: 输出 WAV 路径，None 则创建临时文件
        progress_callback: 进度回调函数，接收 0-100 的整数

    Returns:
        输出 WAV 文件路径

    Raises:
        ValueError: 不支持的目标布局
        Exception: 渲染过程中出错
    """
    import soundfile as sf

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

    def _do_render(src_path: str, dst_path: str, total_samples: int) -> None:
        print(f"[EAR渲染] 开始加载输出布局: {target_layout}")
        spkr_layout, upmix, n_channels = driver.load_output_layout()
        print(f"[EAR渲染] 输出布局加载完成: {n_channels}ch")
        
        print(f"[EAR渲染] 打开 ADM/BW64 文件: {src_path}")
        output_monitor = PeakMonitor(n_channels)

        with openBw64Adm(src_path) as infile:
            print(f"[EAR渲染] ADM 文件已打开，采样率={infile.sampleRate}Hz")
            print(f"[EAR渲染] 开始 validate ADM...")
            infile.adm.validate()
            print(f"[EAR渲染] ADM validate 完成")
            print(f"[EAR渲染] 开始 check blockFormat timings...")
            timing_fixes.check_blockFormat_timings(
                infile.adm, fix=driver.enable_block_duration_fix
            )
            print(f"[EAR渲染] blockFormat timings 检查完成")

            samples_written = 0
            last_percent = -1

            format_info = FormatInfoChunk(
                formatTag=1,
                channelCount=n_channels,
                sampleRate=infile.sampleRate,
                bitsPerSample=infile.bitdepth,
            )
            print(f"[EAR渲染] 打开输出文件: {dst_path} ({n_channels}ch)")
            with openBw64(dst_path, "w", formatInfo=format_info) as outfile:
                print(f"[EAR渲染] 开始 render_input_file 迭代...")
                block_idx = 0
                for output_block in driver.render_input_file(
                    infile, spkr_layout, upmix
                ):
                    if block_idx == 0:
                        print(f"[EAR渲染] 第一个渲染块产出: shape={output_block.shape}")
                    output_monitor.process(output_block)
                    outfile.write(output_block)
                    samples_written += output_block.shape[0]
                    block_idx += 1

                    if progress_callback and total_samples > 0:
                        percent = min(100, int(samples_written / total_samples * 100))
                        if percent != last_percent:
                            progress_callback(percent)
                            last_percent = percent

        print(f"[EAR渲染] 渲染迭代结束，共写出 {samples_written} 采样")
        output_monitor.warn_overloaded()
        if driver.fail_on_overload and output_monitor.has_overloaded():
            raise RuntimeError("输出过载：渲染后的音频出现了削波，请降低增益或检查输入电平。")

    # 用 soundfile 预先获取总样本数（Bw64AdmReader 没有 duration 属性）
    print(f"[EAR渲染] 预读取文件信息: {input_path}")
    info = sf.info(input_path)
    total_samples = info.frames
    print(f"[EAR渲染] 文件信息: {info.frames} frames, {info.channels} ch, {info.samplerate} Hz")

    # 策略 B：先尝试原始文件；若因 audioStreamFormat 双重引用失败，自动修复并重试
    print(f"[EAR渲染] 开始策略B渲染...")
    try:
        _do_render(input_path, output_path, total_samples)
        _ensure_soundfile_compatible(output_path)
        print(f"[EAR渲染] 原始文件渲染成功，输出: {output_path}")
        return output_path
    except Exception as first_err:
        import traceback
        print(f"[EAR渲染] 第一次渲染失败: {first_err}")
        print(traceback.format_exc())
        err_msg = str(first_err)
        if "has a reference to both" in err_msg:
            print("[EAR渲染] 检测到 audioStreamFormat 双重引用，开始流式修复文件...")
            fixed_path = _create_fixed_bw64(input_path, progress_callback=progress_callback)
            try:
                _do_render(fixed_path, output_path, total_samples)
                _ensure_soundfile_compatible(output_path)
                print(f"[EAR渲染] 修复后文件渲染成功，输出: {output_path}")
                return output_path
            finally:
                try:
                    import os
                    os.remove(fixed_path)
                except Exception:
                    pass
        else:
            raise
