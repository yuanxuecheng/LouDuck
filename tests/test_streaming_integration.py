"""集成测试：验证新的流式文件读取 + 流式响度测量

测试逻辑：
1. 从 backups/ 目录解压改造前的旧版 itu1770_meter.py 作为对照；
2. 分别用旧版批处理、新版兼容层、新版真流式处理同一测试音频；
3. 验证三者关键指标一致。

运行前需要在项目根目录（ ImmersiveLoudness/ ）执行。
"""
import sys
import zipfile
import tempfile
import importlib.util
from pathlib import Path
import numpy as np
import soundfile as sf

PROJECT_ROOT = Path(__file__).parent.parent


def load_old_meter_from_backup():
    """从 backups/ 中找到最新的 src-*.zip，解压并加载旧版 ITU1770Meter"""
    backups_dir = PROJECT_ROOT / "backups"
    zips = sorted(backups_dir.glob("src-*.zip"), reverse=True)
    if not zips:
        raise RuntimeError("No backup zip found in backups/")
    
    latest_zip = zips[0]
    print(f"[INFO] Using backup: {latest_zip.name}")
    
    tmpdir = tempfile.mkdtemp(prefix="old_src_")
    with zipfile.ZipFile(latest_zip, 'r') as z:
        z.extract("itu1770_meter.py", tmpdir)
    
    old_path = Path(tmpdir) / "itu1770_meter.py"
    spec = importlib.util.spec_from_file_location("itu1770_meter_old", str(old_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# 加载旧版和新版核心
old_mod = load_old_meter_from_backup()

spec_new = importlib.util.spec_from_file_location(
    "itu1770_meter_new", str(PROJECT_ROOT / "src" / "itu1770_meter.py")
)
new_mod = importlib.util.module_from_spec(spec_new)
spec_new.loader.exec_module(new_mod)


def compare(label, a, b):
    keys = ['integrated', 'short_term', 'momentary', 'true_peak', 'lra',
            'max_short_term', 'max_momentary']
    print(f"\n=== {label} ===")
    all_ok = True
    for k in keys:
        av = a.get(k, -np.inf)
        bv = b.get(k, -np.inf)
        if k == 'lra':
            diff = abs(av - bv)
        elif av == -np.inf or bv == -np.inf:
            diff = 0.0 if av == bv else 999
        else:
            diff = abs(av - bv)
        ok = diff < 1e-6
        all_ok = all_ok and ok
        print(f"  {k:20s}: old={av:+.6f}  new={bv:+.6f}  {'OK' if ok else f'DIFF {diff:.2e}'}")
    
    if a.get('blocks') and b.get('blocks'):
        ba = np.array(a['blocks'])
        bb = np.array(b['blocks'])
        min_len = min(len(ba), len(bb))
        diff = np.max(np.abs(ba[:min_len] - bb[:min_len]))
        ok = diff < 1e-6
        all_ok = all_ok and ok
        print(f"  blocks max diff: {diff:.2e}  {'OK' if ok else 'DIFF'}")
    
    print(f"  curve len: old={len(a.get('short_term_curve', []))}  new={len(b.get('short_term_curve', []))}")
    return all_ok


def ensure_test_audio():
    """生成测试音频（如果不存在）"""
    if not (PROJECT_ROOT / "test_signal.wav").exists():
        np.random.seed(0)
        sr = 48000
        white = np.random.randn(int(sr * 10), 2)
        pink = np.cumsum(white, axis=0)
        pink = pink / np.max(np.abs(pink)) * 0.1
        sf.write(str(PROJECT_ROOT / "test_signal.wav"), pink, sr)
    
    if not (PROJECT_ROOT / "test_signal_44k.wav").exists():
        np.random.seed(1)
        sr = 44100
        white = np.random.randn(int(sr * 5.5), 2)
        pink = np.cumsum(white, axis=0)
        pink = pink / np.max(np.abs(pink)) * 0.15
        sf.write(str(PROJECT_ROOT / "test_signal_44k.wav"), pink, sr)


def test_standard_file(file_path):
    """标准文件模式：旧版 vs 新版兼容层 vs 新版真流式"""
    print(f"\n=== 标准文件模式: {file_path} ===")
    audio, sr = sf.read(str(PROJECT_ROOT / file_path), dtype='float32')
    print(f"  audio: sr={sr}, shape={audio.shape}, duration={len(audio)/sr:.1f}s")
    
    meter_old = old_mod.ITU1770Meter(old_mod.ITU1770Meter.auto_config(audio.shape[1]), sr)
    result_old = meter_old.process_audio(audio, sr)
    
    meter_new = new_mod.ITU1770Meter(new_mod.ITU1770Meter.auto_config(audio.shape[1]), sr)
    result_new_compat = meter_new.process_audio(audio, sr)
    
    meter_new.reset(sr)
    chunk_size = sr  # 1 秒原始采样一块，与新版 process_audio 兼容层一致
    for start in range(0, len(audio), chunk_size):
        meter_new.feed(audio[start:start + chunk_size])
    result_new_stream = meter_new.finalize()
    
    ok1 = compare("旧版 vs 新版兼容层", result_old, result_new_compat)
    ok2 = compare("旧版 vs 新版真流式", result_old, result_new_stream)
    return ok1 and ok2


def test_adm_iter(file_path):
    """测试 adm_parser.iter_audio_blocks"""
    print(f"\n=== ADM 流式读取接口: {file_path} ===")
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from adm_parser import BW64Parser
    
    parser = BW64Parser(str(PROJECT_ROOT / file_path))
    total = 0
    for chunk, sr in parser.iter_audio_blocks(block_samples=48000, dtype='float32'):
        total += chunk.shape[0]
    
    info = sf.info(str(PROJECT_ROOT / file_path))
    ok = total == info.frames
    print(f"  iter total samples: {total}  file frames: {info.frames}  {'OK' if ok else 'FAIL'}")
    return ok


def test_multi_mono():
    """多单声道模式：调用 main_gui._iter_mono_files，旧版 vs 新版真流式"""
    print("\n=== 多单声道模式 ===")
    sr = 48000
    duration = 6.5
    files = []
    for i in range(2):
        np.random.seed(2 + i)
        white = np.random.randn(int(sr * duration))
        pink = np.cumsum(white)
        pink = pink / np.max(np.abs(pink)) * 0.1
        p = PROJECT_ROOT / f"test_mono_{i}.wav"
        sf.write(str(p), pink, sr)
        files.append((str(p), f"Ch{i+1}"))
    
    # 用 main_gui.DetailedMeasurementWorker._iter_mono_files 获取流式迭代器
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from main_gui import DetailedMeasurementWorker
    
    worker = DetailedMeasurementWorker('mono_list', files, '自动检测', None)
    sr0, num_channels, total_samples, audio_iter = worker._iter_mono_files(files)
    
    meter = new_mod.ITU1770Meter(new_mod.ITU1770Meter.auto_config(num_channels), sr0)
    meter.reset(sr0)
    for chunk, _sr in audio_iter:
        meter.feed(chunk)
    result_new = meter.finalize()
    
    # 旧版一次性构造数组
    audio = np.zeros((total_samples, num_channels), dtype='float32')
    for i, (p, _) in enumerate(files):
        data, _ = sf.read(str(p), dtype='float32')
        copy_len = min(len(data), total_samples)
        audio[:copy_len, i] = data[:copy_len]
    
    meter_old = old_mod.ITU1770Meter(old_mod.ITU1770Meter.auto_config(num_channels), sr0)
    result_old = meter_old.process_audio(audio, sr0)
    
    return compare("旧版 vs 新版真流式", result_old, result_new)



if __name__ == '__main__':
    ensure_test_audio()
    
    ok1 = test_standard_file('test_signal.wav')
    ok2 = test_standard_file('test_signal_44k.wav')
    ok3 = test_adm_iter('test_signal.wav')
    ok4 = test_multi_mono()
    
    print("\n=== 汇总 ===")
    print(f"  标准文件 48kHz: {'PASS' if ok1 else 'FAIL'}")
    print(f"  标准文件 44.1kHz: {'PASS' if ok2 else 'FAIL'}")
    print(f"  ADM 迭代器: {'PASS' if ok3 else 'FAIL'}")
    print(f"  多单声道: {'PASS' if ok4 else 'FAIL'}")
