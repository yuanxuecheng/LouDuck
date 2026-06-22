"""
LRA 诊断脚本
加载指定音频，输出 ITU1770Meter 的 LRA 计算中间值，与 FFmpeg(libebur128) 对比
"""
import sys
import numpy as np
import soundfile as sf
from itu1770_meter import ITU1770Meter


def analyze_lra(file_path: str):
    print(f"文件: {file_path}")
    info = sf.info(file_path)
    print(f"采样率: {info.samplerate} Hz, 声道: {info.channels}, 时长: {info.duration:.2f}s")

    audio, sr = sf.read(file_path, dtype='float64')
    if audio.ndim == 1:
        audio = audio.reshape(-1, 1)

    config = ITU1770Meter.auto_config(audio.shape[1])
    meter = ITU1770Meter(config, sr)

    # 手动执行各阶段以获取中间值
    if sr != 48000:
        audio = meter._resample_to_48k(audio, sr)
    filtered = meter._k_weight(audio)
    true_peak = meter._true_peak(audio)
    integrated, blocks = meter._integrated_loudness(filtered)
    (cur_m, cur_s, max_m, max_s, st_100ms, st_1s) = meter._momentary_short_term(filtered)
    lra = meter._lra(st_1s)

    print(f"\n=== 核心结果 ===")
    print(f"Integrated: {integrated:.3f} LKFS")
    print(f"True Peak:  {true_peak:.3f} dBTP")
    print(f"Max Momentary: {max_m:.3f} LKFS")
    print(f"Max Short-term: {max_s:.3f} LKFS")
    print(f"LRA: {lra:.3f} LU")

    print(f"\n=== 1s 步进 Short-term 序列 ({len(st_1s)} 个值) ===")
    st_arr = np.array(st_1s, dtype=np.float64)
    print(f"Min: {np.min(st_arr):.3f}, Max: {np.max(st_arr):.3f}")
    print(f"Mean: {np.mean(st_arr):.3f}, Median: {np.median(st_arr):.3f}")
    print(f"Std: {np.std(st_arr):.3f}")

    print(f"\n=== LRA 门限分析 ===")
    # 绝对门限
    valid = st_arr[st_arr > -70.0]
    print(f"通过绝对门限(-70): {len(valid)}/{len(st_arr)} 个")
    print(f"  被过滤掉的最小值: {np.min(st_arr[st_arr <= -70.0]):.3f}" if np.any(st_arr <= -70.0) else "  无值被绝对门限过滤")

    # 相对门限
    avg = np.mean(valid)
    rel_gate = avg - 20.0
    gated = valid[valid > rel_gate]
    print(f"通过绝对门限后的平均值: {avg:.3f}")
    print(f"相对门限(avg - 20): {rel_gate:.3f}")
    print(f"通过双门限: {len(gated)}/{len(valid)} 个")
    if len(gated) > 0:
        print(f"  Gated Min: {np.min(gated):.3f}, Gated Max: {np.max(gated):.3f}")
        print(f"  P10: {np.percentile(gated, 10.0):.3f}")
        print(f"  P95: {np.percentile(gated, 95.0):.3f}")
        print(f"  P95 - P10 = {np.percentile(gated, 95.0) - np.percentile(gated, 10.0):.3f}")

    # 对比：如果不用门限
    print(f"\n=== 无门限参考 ===")
    print(f"P10 (all): {np.percentile(st_arr, 10.0):.3f}")
    print(f"P95 (all): {np.percentile(st_arr, 95.0):.3f}")
    print(f"P95-P10 (all): {np.percentile(st_arr, 95.0) - np.percentile(st_arr, 10.0):.3f}")

    # 对比：如果只用绝对门限
    print(f"\n=== 仅绝对门限参考 ===")
    print(f"P10 (abs-gated): {np.percentile(valid, 10.0):.3f}")
    print(f"P95 (abs-gated): {np.percentile(valid, 95.0):.3f}")
    print(f"P95-P10 (abs-gated): {np.percentile(valid, 95.0) - np.percentile(valid, 10.0):.3f}")

    # 对比：不同相对门限
    for offset in [15, 18, 20, 22]:
        g = valid[valid > (avg - offset)]
        if len(g) >= 2:
            print(f"\n=== 相对门限 avg - {offset} LU ({len(g)} 个) ===")
            print(f"  P10: {np.percentile(g, 10.0):.3f}, P95: {np.percentile(g, 95.0):.3f}")
            print(f"  LRA: {np.percentile(g, 95.0) - np.percentile(g, 10.0):.3f}")

    # 输出前20个和后20个 short-term 值
    print(f"\n=== Short-term 值序列 (前20) ===")
    for i, v in enumerate(st_1s[:20]):
        print(f"  [{i:3d}] {v:+.3f} LKFS")
    if len(st_1s) > 40:
        print(f"  ... ({len(st_1s)-40} values omitted) ...")
    print(f"=== Short-term 值序列 (后20) ===")
    for i, v in enumerate(st_1s[-20:], start=len(st_1s)-20):
        print(f"  [{i:3d}] {v:+.3f} LKFS")


if __name__ == '__main__':
    path = r"D:\new workzone\test files for loudness test\贝五-5.1-1M19S-WLM-20.6LKFS-6.7dBTP-8LU.wav"
    if len(sys.argv) > 1:
        path = sys.argv[1]
    analyze_lra(path)
