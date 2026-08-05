#!/usr/bin/env python3
"""ADM/BW64/RF64 大文件诊断脚本。

用法：
    python src/diagnose_adm.py "/path/to/large_adm.wav"

输出文件头信息、soundfile 读取结果、is_adm_file 检测结果以及
BW64Parser 解析结果，用于定位大文件 ADM 元数据无法识别的问题。
"""

import struct
import sys
import time
import traceback
from pathlib import Path


def read_header(path: str):
    with open(path, 'rb') as f:
        header = f.read(12)
    return header


def main():
    if len(sys.argv) < 2:
        print("用法: python diagnose_adm.py <文件路径>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    p = Path(path)
    print(f"文件路径: {path}")
    print(f"文件存在: {p.exists()}")
    if p.exists():
        size = p.stat().st_size
        print(f"文件大小: {size} bytes ({size / (1024 ** 3):.3f} GB)")
    print(f"扩展名: {p.suffix}")

    print("\n=== 原始文件头 (前 12 字节) ===")
    try:
        header = read_header(path)
        print(f"  原始 bytes: {header!r}")
        if len(header) >= 12:
            riff_id = header[:4]
            file_size_32 = struct.unpack('<I', header[4:8])[0]
            form_id = header[8:12]
            print(f"  RIFF ID: {riff_id!r}")
            print(f"  32-bit size: {file_size_32} (0x{file_size_32:08x})")
            print(f"  Form ID: {form_id!r}")
    except Exception as e:
        print(f"  读取失败: {e}")
        traceback.print_exc()

    print("\n=== soundfile info ===")
    try:
        import soundfile as sf
        t0 = time.time()
        info = sf.info(path)
        print(f"  耗时: {time.time() - t0:.3f}s")
        print(f"  channels={info.channels}, samplerate={info.samplerate}, "
              f"duration={info.duration:.3f}s, subtype={info.subtype!r}, "
              f"format={info.format!r}")
    except Exception as e:
        print(f"  错误: {e}")
        traceback.print_exc()

    print("\n=== is_adm_file ===")
    try:
        from adm_parser import is_adm_file
        t0 = time.time()
        result = is_adm_file(path)
        print(f"  耗时: {time.time() - t0:.3f}s")
        print(f"  结果: {result}")
    except Exception as e:
        print(f"  错误: {e}")
        traceback.print_exc()

    print("\n=== BW64Parser.parse ===")
    try:
        from adm_parser import BW64Parser
        t0 = time.time()
        parser = BW64Parser(path)
        adm = parser.parse()
        print(f"  耗时: {time.time() - t0:.3f}s")
        print(f"  programme_name: {getattr(adm, 'programme_name', None)!r}")
        print(f"  content: {getattr(adm, 'content', None)!r}")
        print(f"  renderer: {getattr(adm, 'renderer', None)!r}")
        print(f"  audio_info: {getattr(parser, 'audio_info', None)!r}")
        print(f"  axml_size: {len(getattr(parser, 'axml_data', b''))}")
        print(f"  chna_size: {len(getattr(parser, 'chna_data', b''))}")
        print(f"  auto_detect_config: {adm.auto_detect_config()!r}")
    except Exception as e:
        print(f"  错误: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
