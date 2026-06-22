"""大文件流式处理内存测试（使用 tracemalloc）"""
import sys
import time
import tracemalloc
import soundfile as sf

sys.path.insert(0, 'src')
from itu1770_meter import ITU1770Meter

file_path = 'test_big_10ch.wav'
info = sf.info(file_path)
print(f"File: {file_path}")
print(f"  sr={info.samplerate}, channels={info.channels}, frames={info.frames}, duration={info.duration:.1f}s")
print(f"  file size: {info.frames * info.channels * 4 / 1024 / 1024:.1f} MB (float32 equivalent)")

tracemalloc.start()
start_mem, _ = tracemalloc.get_traced_memory()
start_mem_mb = start_mem / 1024 / 1024
print(f"\nStart memory: {start_mem_mb:.1f} MB")

meter = ITU1770Meter(ITU1770Meter.auto_config(info.channels), info.samplerate)
meter.reset(info.samplerate)

peak_mem_mb = start_mem_mb
start_time = time.time()
processed = 0

with sf.SoundFile(file_path, 'r') as f:
    for chunk in f.blocks(blocksize=info.samplerate, dtype='float32', always_2d=True):
        meter.feed(chunk)
        processed += chunk.shape[0]
        current_mem, _ = tracemalloc.get_traced_memory()
        current_mem_mb = current_mem / 1024 / 1024
        if current_mem_mb > peak_mem_mb:
            peak_mem_mb = current_mem_mb
        if (processed // info.samplerate) % 5 == 0:
            print(f"  processed {processed/info.samplerate:.1f}s, current mem {current_mem_mb:.1f} MB")

result = meter.finalize()
elapsed = time.time() - start_time
end_mem, _ = tracemalloc.get_traced_memory()
end_mem_mb = end_mem / 1024 / 1024

tracemalloc.stop()

print(f"\nProcessing time: {elapsed:.1f}s")
print(f"Speed ratio: {info.duration/elapsed:.1f}x real-time")
print(f"Peak memory: {peak_mem_mb:.1f} MB")
print(f"Memory delta (peak - start): {peak_mem_mb - start_mem_mb:.1f} MB")
print(f"\nResults:")
print(f"  integrated: {result['integrated']:+.2f} LKFS")
print(f"  max_short_term: {result['max_short_term']:+.2f} LKFS")
print(f"  max_momentary: {result['max_momentary']:+.2f} LKFS")
print(f"  true_peak: {result['true_peak']:+.2f} dBTP")
print(f"  lra: {result['lra']:.2f} LU")
