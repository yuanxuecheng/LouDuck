"""
ITU-R BS.1770-5 响度测量核心算法（真流式/状态机版）

算法依据：
- ITU-R BS.1770-5 (2023) — 集成响度、真峰值、声道加权
- EBU Tech 3341 (2016) — Momentary / Short-term 定义
- EBU Tech 3342 (2016) — 响度范围 LRA

关键标准要点：
1. K-加权滤波：两段级联 IIR（Stage1 高通 + Stage2 高频 shelf），
   仅使用 48kHz 标准系数（Table 1/2）。非 48kHz 输入先重采样。
2. 集成响度：
   - 400ms 不重叠 gating blocks（48kHz 下每块 19200 采样）。
   - 每块加权功率 z_i = Σ G_j · mean_sq_j。
   - 块响度 l_i = -0.691 + 10·log10(z_i)。
   - 绝对门限：-70.0 LKFS（功率域等效门限 10^(-6.9309)）。
   - 相对门限：通过绝对门限的块的平均功率 × 0.1（即平均响度 -10 LU 的功率等效）。
   - 集成响度 = 通过双门限的所有块的平均 z 转 dB（公式 2）。
3. 真峰值：原始音频 4x 过采样 FIR（48 阶 4 相，Annex 2）。
   流式处理时保存 FIR 尾部历史，保证跨块边界峰值不丢失。
4. Momentary：400ms 滑动窗口，100ms 步进（EBU Tech 3341）。
5. Short-term：3s 滑动窗口，100ms 步进（EBU Tech 3341）。
6. LRA：基于 3s 窗口、1s 步进的 Short-term 序列，双门限后取 10%~95% 分位差（EBU Tech 3342）。

流式接口：
    meter = ITU1770Meter(config, sr)
    meter.reset(sr)
    for chunk in audio_chunks:
        meter.feed(chunk)
    result = meter.finalize()

兼容性接口：
    result = meter.process_audio(audio, sr, progress_callback)
    内部已被实现为流式接口的薄封装，结果字段与旧版完全一致。

进度回调：
    progress_callback(step_name: str, overall_progress_pct: float)
    step_name: 当前计算步骤（中文）
    overall_progress_pct: 0.0 ~ 100.0，反映整个测量流程的进度
"""

import numpy as np
from scipy import signal
from dataclasses import dataclass
from typing import List, Optional, Callable
from collections import deque


@dataclass
class ChannelConfig:
    """声道配置"""
    name: str
    azimuth: float
    elevation: float
    is_lfe: bool = False

    def get_weight(self) -> float:
        """ITU-R BS.1770-5 Table 4 权重"""
        if self.is_lfe:
            return 0.0
        abs_az = abs(self.azimuth)
        abs_el = abs(self.elevation)
        # 顶部声道（仰角 ≥ 30°）
        if abs_el >= 30.0:
            return 1.0
        # 前方 / 后方（仰角 < 30°）
        if abs_az < 60.0:
            return 1.0
        elif abs_az <= 120.0:
            return 1.41  # +1.5 dB，线性值
        else:
            return 1.0


class ITU1770Meter:
    """ITU-R BS.1770-5 响度计（真流式/状态机实现）"""

    # 48kHz K-加权滤波器系数（Table 1 / Table 2）
    STAGE1_B = [1.53512485958697, -2.69169618940638, 1.19839281085285]
    STAGE1_A = [1.0, -1.69065929318241, 0.73248077421585]
    STAGE2_B = [1.0, -2.0, 1.0]
    STAGE2_A = [1.0, -1.99004745483398, 0.99007225036621]

    # 真峰值 FIR 系数（Annex 2，48 阶 4 相）
    TP_FIR = np.array([
        0.0017089843750, -0.0291748046875, -0.0189208984375, -0.0083007812500,
        0.0109863281250, 0.0292968750000, 0.0330810546875, 0.0148925781250,
        -0.0196533203125, -0.0517578125000, -0.0582275390625, -0.0266113281250,
        0.0332031250000, 0.0891113281250, 0.1015625000000, 0.0476074218750,
        -0.0594482421875, -0.1665039062500, -0.2003173828125, -0.1022949218750,
        0.1373291015625, 0.4650878906250, 0.7797851562500, 0.9721679687500,
        0.9721679687500, 0.7797851562500, 0.4650878906250, 0.1373291015625,
        -0.1022949218750, -0.2003173828125, -0.1665039062500, -0.0594482421875,
        0.0476074218750, 0.1015625000000, 0.0891113281250, 0.0332031250000,
        -0.0266113281250, -0.0582275390625, -0.0517578125000, -0.0196533203125,
        0.0148925781250, 0.0330810546875, 0.0292968750000, 0.0109863281250,
        -0.0083007812500, -0.0189208984375, -0.0291748046875, 0.0017089843750
    ], dtype=np.float64)

    # 标准声道配置
    CONFIGS = {
        'stereo': [
            ChannelConfig('L', 30, 0), ChannelConfig('R', -30, 0)
        ],
        '5.1': [
            ChannelConfig('L', 30, 0), ChannelConfig('R', -30, 0),
            ChannelConfig('C', 0, 0), ChannelConfig('LFE', 0, 0, True),
            ChannelConfig('Ls', 110, 0), ChannelConfig('Rs', -110, 0),
        ],
        '7.1': [
            ChannelConfig('L', 30, 0), ChannelConfig('R', -30, 0),
            ChannelConfig('C', 0, 0), ChannelConfig('LFE', 0, 0, True),
            ChannelConfig('Lss', 90, 0), ChannelConfig('Rss', -90, 0),
            ChannelConfig('Lrs', 135, 0), ChannelConfig('Rrs', -135, 0),
        ],
        '5.1.4': [
            ChannelConfig('L', 30, 0), ChannelConfig('R', -30, 0),
            ChannelConfig('C', 0, 0), ChannelConfig('LFE', 0, 0, True),
            ChannelConfig('Ls', 110, 0), ChannelConfig('Rs', -110, 0),
            ChannelConfig('Ltf', 45, 45), ChannelConfig('Rtf', -45, 45),
            ChannelConfig('Ltr', 135, 45), ChannelConfig('Rtr', -135, 45),
        ],
        '7.1.2': [
            ChannelConfig('L', 30, 0), ChannelConfig('R', -30, 0),
            ChannelConfig('C', 0, 0), ChannelConfig('LFE', 0, 0, True),
            ChannelConfig('Lss', 90, 0), ChannelConfig('Rss', -90, 0),
            ChannelConfig('Lrs', 135, 0), ChannelConfig('Rrs', -135, 0),
            ChannelConfig('Ltf', 45, 45), ChannelConfig('Rtf', -45, 45),
        ],
        '7.1.4': [
            ChannelConfig('L', 30, 0), ChannelConfig('R', -30, 0),
            ChannelConfig('C', 0, 0), ChannelConfig('LFE', 0, 0, True),
            ChannelConfig('Lss', 90, 0), ChannelConfig('Rss', -90, 0),
            ChannelConfig('Lrs', 135, 0), ChannelConfig('Rrs', -135, 0),
            ChannelConfig('Ltf', 45, 45), ChannelConfig('Rtf', -45, 45),
            ChannelConfig('Ltb', 135, 45), ChannelConfig('Rtb', -135, 45),
        ],
    }

    def __init__(self, channel_config: List[ChannelConfig], sample_rate: int = 48000):
        self.channel_config = channel_config
        self.sample_rate = sample_rate
        self.weights = [ch.get_weight() for ch in channel_config]
        self._reset_state()

    @classmethod
    def auto_config(cls, num_channels: int) -> List[ChannelConfig]:
        """根据声道数自动选择配置"""
        mapping = {2: 'stereo', 6: '5.1', 8: '7.1', 10: '5.1.4', 12: '7.1.4'}
        config_name = mapping.get(num_channels, 'stereo')
        return cls.CONFIGS.get(config_name, cls.CONFIGS['stereo'])

    # ------------------------------------------------------------------ #
    # 状态管理
    # ------------------------------------------------------------------ #

    def _reset_state(self):
        """重置所有流式状态"""
        num_channels = len(self.channel_config)

        # K-加权滤波器状态（每声道独立，初始为 0，与整段 lfilter 默认行为一致）
        self._zi_stage1 = [np.zeros(max(len(self.STAGE1_A), len(self.STAGE1_B)) - 1,
                                    dtype=np.float64) for _ in range(num_channels)]
        self._zi_stage2 = [np.zeros(max(len(self.STAGE2_A), len(self.STAGE2_B)) - 1,
                                    dtype=np.float64) for _ in range(num_channels)]

        # 100ms 功率累积器
        self._power_buffer = 0.0
        self._power_buffer_samples = 0

        # 100ms 块功率序列（用于 Momentary / Short-term）
        self._z_100ms_window = deque()

        # 400ms 块统计（用于 Integrated）
        self._z_values = []          # 线性功率
        self._blocks_loudness = []   # LKFS

        # Momentary / Short-term
        self._momentary_values = []
        self._short_term_values_100ms = []
        self._short_term_values_1s = []

        # 真峰值
        self._max_tp_linear = 0.0
        self._tp_tail_raw = [np.array([], dtype=np.float64) for _ in range(num_channels)]

        # 采样率与计数
        self._input_sr = self.sample_rate
        self._processed_samples_48k = 0

    def reset(self, sample_rate: int = 48000):
        """公开接口：重置测量器，准备处理新文件"""
        self._input_sr = sample_rate
        self._reset_state()

    # ------------------------------------------------------------------ #
    # 内部工具方法
    # ------------------------------------------------------------------ #

    @staticmethod
    def _cb(callback: Optional[Callable], step: str, pct: float):
        """安全调用进度回调"""
        if callback is not None:
            callback(step, float(pct))

    @staticmethod
    def _to_db(power: float) -> float:
        """功率转 LKFS"""
        if power > 0.0:
            return -0.691 + 10.0 * np.log10(power)
        return -np.inf

    def _resample_chunk(self, chunk: np.ndarray, sr: int) -> np.ndarray:
        """将单块音频重采样到 48kHz（resample_poly 是 LTI，可分块无状态处理）"""
        if sr == 48000:
            return chunk

        target_sr = 48000
        g = int(np.gcd(sr, target_sr))
        up = target_sr // g
        down = sr // g
        return signal.resample_poly(chunk, up, down, axis=0)

    def _k_weight_feed(self, chunk: np.ndarray) -> np.ndarray:
        """K-加权滤波（流式，状态保持）"""
        num_channels = chunk.shape[1]
        filtered = np.empty_like(chunk, dtype=np.float64)

        for ch in range(num_channels):
            x = chunk[:, ch].astype(np.float64)
            y1, zf1 = signal.lfilter(
                self.STAGE1_B, self.STAGE1_A, x, zi=self._zi_stage1[ch]
            )
            self._zi_stage1[ch] = zf1

            y2, zf2 = signal.lfilter(
                self.STAGE2_B, self.STAGE2_A, y1, zi=self._zi_stage2[ch]
            )
            self._zi_stage2[ch] = zf2

            filtered[:, ch] = y2

        return filtered

    def _weighted_power_per_sample(self, filtered: np.ndarray) -> np.ndarray:
        """计算每个采样点的加权功率（跨声道求和，跳过 LFE）"""
        n_samples = filtered.shape[0]
        power = np.zeros(n_samples, dtype=np.float64)
        num_channels = min(filtered.shape[1], len(self.channel_config))

        for j in range(num_channels):
            ch_cfg = self.channel_config[j]
            if ch_cfg.is_lfe:
                continue
            w = self.weights[j]
            if w > 0.0:
                power += w * (filtered[:, j].astype(np.float64) ** 2)

        return power

    def _on_100ms_block(self, z: float):
        """每生成一个 100ms 块时调用，更新所有依赖统计量"""
        self._z_100ms_window.append(z)
        idx = len(self._z_100ms_window) - 1

        # Momentary: 400ms 滑动窗口，100ms 步进
        if idx >= 3:
            window = list(self._z_100ms_window)[-4:]
            mean_z = np.mean(window)
            self._momentary_values.append(self._to_db(mean_z))

        # Short-term (EBU Tech 3341): 3s 滑动窗口，100ms 步进
        if idx >= 29:
            window = list(self._z_100ms_window)[-30:]
            mean_z = np.mean(window)
            self._short_term_values_100ms.append(self._to_db(mean_z))

        # 注意：1s 步进的 Short-term（用于 LRA）需要在所有 100ms 块都产生后，
        # 在 finalize() 中统一计算，因为以当前块为起始的 3s 窗口需要未来的块。

    def _accumulate_power(self, filtered: np.ndarray):
        """累积 100ms 功率块，并生成 400ms 集成响度块"""
        sr = 48000
        win_100ms = int(0.1 * sr)  # 4800 samples

        if win_100ms <= 0:
            return

        power = self._weighted_power_per_sample(filtered)
        n_samples = len(power)
        pos = 0

        while pos < n_samples:
            need = win_100ms - self._power_buffer_samples
            available = n_samples - pos

            if available >= need:
                # 可以完成一个 100ms 块
                self._power_buffer += np.sum(power[pos:pos + need])
                z_100ms = self._power_buffer / win_100ms

                self._on_100ms_block(z_100ms)

                # 检查是否凑齐 4 个 100ms 块（一个不重叠 400ms 块）
                if len(self._z_100ms_window) % 4 == 0:
                    block_idx = len(self._z_100ms_window) - 4
                    block_window = list(self._z_100ms_window)[block_idx:block_idx + 4]
                    z_block = np.mean(block_window)
                    self._z_values.append(z_block)
                    self._blocks_loudness.append(self._to_db(z_block))

                # 重置缓冲
                self._power_buffer = 0.0
                self._power_buffer_samples = 0
                pos += need
            else:
                # 不足以完成一个 100ms 块，累积到缓冲
                self._power_buffer += np.sum(power[pos:])
                self._power_buffer_samples += available
                pos = n_samples

    def _true_peak_feed(self, chunk: np.ndarray):
        """真峰值流式测量（4x 过采样 FIR，保存尾部历史）"""
        num_channels = chunk.shape[1]
        fir_len = len(self.TP_FIR)
        tail_len = fir_len - 1  # 48 -> 47

        for ch in range(num_channels):
            x = chunk[:, ch].astype(np.float64)
            tail = self._tp_tail_raw[ch]

            if len(tail) > 0:
                x_concat = np.concatenate([tail, x])
            else:
                x_concat = x

            # 4x 上采样
            x_up = np.zeros(len(x_concat) * 4, dtype=np.float64)
            x_up[::4] = x_concat

            # FIR 滤波
            y = signal.lfilter(self.TP_FIR, [1.0], x_up)

            # 有效输出区段：跳过上一块 tail 对应的输出，只取当前 chunk 的 4x 样点
            valid_start = len(tail) * 4
            valid_end = valid_start + len(x) * 4
            valid_y = y[valid_start:valid_end]

            if len(valid_y) > 0:
                tp = np.max(np.abs(valid_y))
                if tp > self._max_tp_linear:
                    self._max_tp_linear = tp

            # 保存当前块尾部原始采样供下一块使用
            new_tail_len = min(tail_len, len(x))
            if new_tail_len > 0:
                self._tp_tail_raw[ch] = x[-new_tail_len:].copy()
            else:
                self._tp_tail_raw[ch] = np.array([], dtype=np.float64)

    def _compute_short_term_1s(self):
        """在所有 100ms 块累积完成后，计算 3s 窗口、1s 步进的 Short-term（用于 LRA）"""
        s_win = 30
        z_list = list(self._z_100ms_window)
        self._short_term_values_1s = []
        for i in range(0, len(z_list) - s_win + 1, 10):
            window = z_list[i:i + s_win]
            mean_z = np.mean(window)
            self._short_term_values_1s.append(self._to_db(mean_z))

    def _integrated_loudness(self) -> Tuple[float, List[float]]:
        """基于已累积的 400ms 块计算集成响度"""
        z_arr = np.array(self._z_values, dtype=np.float64)

        if len(z_arr) == 0:
            return -np.inf, self._blocks_loudness

        # Step 2: 绝对门限 -70.0 LKFS
        abs_threshold_power = 10.0 ** ((-70.0 + 0.691) / 10.0)
        abs_mask = z_arr > abs_threshold_power

        if not np.any(abs_mask):
            return -np.inf, self._blocks_loudness

        # Step 3: 相对门限 = 通过绝对门限的块的平均响度 - 10 LU
        mean_z_abs = np.mean(z_arr[abs_mask])
        rel_threshold_power = mean_z_abs / 10.0

        # Step 4: 双门限筛选
        final_mask = z_arr > rel_threshold_power
        if not np.any(final_mask):
            return -np.inf, self._blocks_loudness

        # Step 5: 集成响度 = 通过双门限的块的平均 z 转 dB
        mean_z_final = np.mean(z_arr[final_mask])
        integrated = -0.691 + 10.0 * np.log10(mean_z_final)

        return float(integrated), self._blocks_loudness

    @staticmethod
    def _lra(short_term_values: List[float]) -> float:
        """响度范围 LRA（EBU Tech 3342）"""
        if not short_term_values:
            return 0.0

        st_arr = np.array(short_term_values, dtype=np.float64)

        # 第一门限：-70.0 LKFS
        valid = st_arr[st_arr > -70.0]
        if len(valid) < 2:
            return 0.0

        # 第二门限：平均值 - 20 LU
        avg = np.mean(valid)
        second_gate = avg - 20.0

        gated = valid[valid > second_gate]
        if len(gated) < 2:
            return 0.0

        p10 = np.percentile(gated, 10.0)
        p95 = np.percentile(gated, 95.0)

        return float(max(0.0, p95 - p10))

    # ------------------------------------------------------------------ #
    # 公共接口
    # ------------------------------------------------------------------ #

    def feed(self, chunk: np.ndarray,
             progress_callback: Optional[Callable] = None,
             overall_progress: Optional[float] = None):
        """
        流式喂入一块音频数据。

        Args:
            chunk: 音频数据，shape 为 (samples,) 或 (samples, channels)
            progress_callback: 进度回调，签名为 (step_name, overall_progress_pct)
            overall_progress: 0.0~100.0 之间的浮点数，表示当前 chunk 在整个文件中的进度。
                              如果不提供，只在回调中报告 "流式处理" 步骤。
        """
        if chunk is None or len(chunk) == 0:
            return

        # 标准化输入维度
        if chunk.ndim == 1:
            chunk = chunk.reshape(-1, 1)
        chunk = np.asarray(chunk, dtype=np.float64)

        actual_sr = self._input_sr

        # 流式化后，单个 chunk 内同时完成重采样/K-加权/真峰值/响度统计，
        # 不再区分传统“步骤”，只报告统一进度。
        pct = overall_progress if overall_progress is not None else 0.0
        self._cb(progress_callback, "流式响度测量", pct)

        # ---- 阶段 1: 重采样到 48kHz ----
        if actual_sr != 48000:
            chunk = self._resample_chunk(chunk, actual_sr)

        # ---- 阶段 2: K-加权滤波 ----
        filtered = self._k_weight_feed(chunk)

        # ---- 阶段 3: 真峰值 ----
        self._true_peak_feed(chunk)

        # ---- 阶段 4 & 5: 累积功率、集成响度块、Momentary / Short-term ----
        self._accumulate_power(filtered)

        self._processed_samples_48k += len(filtered)

    def finalize(self, progress_callback: Optional[Callable] = None) -> dict:
        """
        结束流式处理，返回完整测量结果。

        Returns:
            dict，字段与 process_audio() 完全一致：
                integrated: float      # 集成响度 LKFS
                short_term: float      # 当前/最后短时响度 LKFS
                momentary: float       # 当前/最后瞬时响度 LKFS
                true_peak: float       # 最大真峰值 dBTP
                lra: float             # 响度范围 LU
                max_short_term: float  # 最大短时响度
                max_momentary: float   # 最大瞬时响度
                blocks: List[float]    # 400ms 块响度序列（LKFS）
                short_term_curve: List[float]  # 1s 步进短时响度序列
        """
        self._cb(progress_callback, "计算集成响度", 25.0)
        integrated, blocks_loudness = self._integrated_loudness()

        self._cb(progress_callback, "计算响度范围", 80.0)
        self._compute_short_term_1s()
        lra = self._lra(self._short_term_values_1s)

        self._cb(progress_callback, "整理结果", 95.0)

        max_momentary = max(self._momentary_values) if self._momentary_values else -np.inf
        max_short_term = max(self._short_term_values_100ms) if self._short_term_values_100ms else -np.inf
        current_momentary = self._momentary_values[-1] if self._momentary_values else -np.inf
        current_short_term = self._short_term_values_100ms[-1] if self._short_term_values_100ms else -np.inf
        true_peak_db = 20.0 * np.log10(self._max_tp_linear) if self._max_tp_linear > 0.0 else -np.inf

        result = {
            'integrated': integrated,
            'short_term': current_short_term,
            'momentary': current_momentary,
            'true_peak': true_peak_db,
            'lra': lra,
            'max_short_term': max_short_term,
            'max_momentary': max_momentary,
            'blocks': blocks_loudness,
            'short_term_curve': list(self._short_term_values_1s),
        }

        self._cb(progress_callback, "测量完成", 100.0)
        return result

    def process_audio(self, audio: np.ndarray, sr: Optional[int] = None,
                      progress_callback: Optional[Callable] = None) -> dict:
        """
        兼容旧接口：处理完整音频并返回测量结果。
        内部已被实现为流式接口的薄封装，结果与新流式接口一致。

        Args:
            audio: 音频数据，shape 为 (samples,) 或 (samples, channels)
            sr: 原始采样率。若非 48000，会先重采样到 48000。
            progress_callback: 进度回调，签名为 (step_name, overall_progress_pct)

        Returns:
            dict，与 finalize() 返回字段相同。
        """
        if audio is None or len(audio) == 0:
            return {
                'integrated': -np.inf, 'short_term': -np.inf,
                'momentary': -np.inf, 'true_peak': -np.inf,
                'lra': 0.0, 'max_short_term': -np.inf,
                'max_momentary': -np.inf, 'blocks': [],
                'short_term_curve': []
            }

        actual_sr = sr if sr is not None else self.sample_rate
        self.reset(actual_sr)

        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        audio = np.asarray(audio, dtype=np.float64)

        total_samples = len(audio)
        chunk_samples = actual_sr  # 1 秒原始采样一块，与旧版 _resample_to_48k 分块一致

        for start in range(0, total_samples, chunk_samples):
            end = min(start + chunk_samples, total_samples)
            chunk = audio[start:end]
            progress = (end / total_samples) * 100.0 if total_samples > 0 else 100.0
            self.feed(chunk, progress_callback=progress_callback, overall_progress=progress)

        return self.finalize(progress_callback=progress_callback)
