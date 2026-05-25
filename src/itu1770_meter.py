"""
ITU-R BS.1770-5 响度测量核心算法（严格遵循标准重写版）

算法依据：
- ITU-R BS.1770-5 (2023) — 集成响度、真峰值、声道加权
- EBU Tech 3341 (2016) — Momentary / Short-term 定义
- EBU Tech 3342 (2016) — 响度范围 LRA

关键标准要点：
1. K-加权滤波：整段连续应用两段级联 IIR（Stage1 高通 + Stage2 高频 shelf），
   仅使用 48kHz 标准系数（Table 1/2）。非 48kHz 输入先重采样。
2. 集成响度：
   - 400ms 不重叠 gating blocks（48kHz 下每块 19200 采样）。
   - 每块加权功率 z_i = Σ G_j · mean_sq_j。
   - 块响度 l_i = -0.691 + 10·log10(z_i)。
   - 绝对门限：-70.0 LUFS（功率域等效门限 10^(-6.9309)）。
   - 相对门限：通过绝对门限的块的平均功率 × 0.1（即平均响度 -10 LU 的功率等效）。
   - 集成响度 = 通过双门限的所有块的平均 z 转 dB（公式 2）。
3. 真峰值：原始音频整段 4x 过采样 FIR（48 阶 4 相，Annex 2），避免分块边界失真。
4. Momentary：400ms 滑动窗口，100ms 步进（EBU Tech 3341）。
5. Short-term：3s 滑动窗口，100ms 步进（EBU Tech 3341）。
6. LRA：基于 Short-term 序列，双门限后取 10%~95% 分位差（EBU Tech 3342）。

进度回调：
    progress_callback(step_name: str, overall_progress_pct: float)
    step_name: 当前计算步骤（中文）
    overall_progress_pct: 0.0 ~ 100.0，反映整个测量流程的进度
"""

import numpy as np
from scipy import signal
from dataclasses import dataclass
from typing import List, Optional, Callable


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
    """ITU-R BS.1770-5 响度计"""

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

    @classmethod
    def auto_config(cls, num_channels: int) -> List[ChannelConfig]:
        """根据声道数自动选择配置"""
        mapping = {2: 'stereo', 6: '5.1', 8: '7.1', 10: '5.1.4', 12: '7.1.4'}
        config_name = mapping.get(num_channels, 'stereo')
        return cls.CONFIGS.get(config_name, cls.CONFIGS['stereo'])

    # ------------------------------------------------------------------ #
    # 内部工具方法
    # ------------------------------------------------------------------ #

    @staticmethod
    def _cb(callback: Optional[Callable], step: str, pct: float):
        """安全调用进度回调"""
        if callback is not None:
            callback(step, float(pct))

    def _resample_to_48k(self, audio: np.ndarray, sr: int,
                         callback: Optional[Callable] = None) -> np.ndarray:
        """重采样到 48kHz，分块处理以支持进度报告"""
        if sr == 48000:
            return audio

        target_sr = 48000
        g = int(np.gcd(sr, target_sr))
        up = target_sr // g
        down = sr // g

        # 每块处理约 1 秒原始音频，避免内存暴涨
        chunk_samples = sr
        num_chunks = max(1, (len(audio) + chunk_samples - 1) // chunk_samples)
        resampled_chunks = []

        for i in range(num_chunks):
            start = i * chunk_samples
            end = min(start + chunk_samples, len(audio))
            chunk = audio[start:end]
            resampled = signal.resample_poly(chunk, up, down, axis=0)
            resampled_chunks.append(resampled)

            pct = (i + 1) / num_chunks * 15.0
            self._cb(callback, "重采样到 48kHz", pct)

        return np.concatenate(resampled_chunks, axis=0)

    def _k_weight(self, audio: np.ndarray) -> np.ndarray:
        """K-加权滤波（整段连续，避免分块状态重置）"""
        y1 = signal.lfilter(self.STAGE1_B, self.STAGE1_A, audio, axis=0)
        y2 = signal.lfilter(self.STAGE2_B, self.STAGE2_A, y1, axis=0)
        return y2

    def _true_peak(self, audio: np.ndarray,
                   callback: Optional[Callable] = None) -> float:
        """真峰值测量（整段原始音频，4x 过采样 FIR）"""
        max_tp = 0.0
        num_ch = audio.shape[1]
        for ch in range(num_ch):
            x = audio[:, ch].astype(np.float64)
            x_up = np.zeros(len(x) * 4, dtype=np.float64)
            x_up[::4] = x
            y = signal.lfilter(self.TP_FIR, [1.0], x_up)
            tp = np.max(np.abs(y))
            if tp > max_tp:
                max_tp = tp
            pct = 20.0 + (ch + 1) / num_ch * 5.0
            self._cb(callback, "计算真峰值", pct)
        if max_tp > 0.0:
            return 20.0 * np.log10(max_tp)
        return -np.inf

    def _weighted_power(self, block: np.ndarray) -> float:
        """
        计算单一块的加权功率 z = Σ G_j · mean_sq_j
        block: (samples, channels)
        """
        weighted_sum = 0.0
        for j, ch_cfg in enumerate(self.channel_config):
            if ch_cfg.is_lfe or j >= block.shape[1]:
                continue
            w = self.weights[j]
            if w > 0.0:
                # 使用 float64 避免精度问题
                mean_sq = np.mean(block[:, j].astype(np.float64) ** 2)
                weighted_sum += w * mean_sq
        return weighted_sum

    def _integrated_loudness(self, filtered: np.ndarray,
                             callback: Optional[Callable] = None):
        """
        集成响度（ITU-R BS.1770-5 公式 1 / 2）
        返回: (integrated_lufs, blocks_loudness_list)
        """
        sr = 48000
        block_samples = int(0.4 * sr)          # 400ms = 19200 samples
        num_samples = len(filtered)
        num_blocks = num_samples // block_samples

        if num_blocks == 0:
            return -np.inf, []

        z_values = []          # 每块的加权功率（线性）
        blocks_loudness = []   # 每块的响度 l_i（LUFS），用于 GUI 曲线

        report_interval = max(1, num_blocks // 20)

        for i in range(num_blocks):
            start = i * block_samples
            end = start + block_samples
            block = filtered[start:end]

            z = self._weighted_power(block)
            z_values.append(z)

            if z > 0.0:
                l = -0.691 + 10.0 * np.log10(z)
            else:
                l = -np.inf
            blocks_loudness.append(l)

            if callback and (i + 1) % report_interval == 0:
                pct = 25.0 + (i + 1) / num_blocks * 25.0  # 集成响度占 25~50%
                self._cb(callback, "计算集成响度", pct)

        z_arr = np.array(z_values, dtype=np.float64)

        # Step 2: 绝对门限 -70.0 LUFS（转成功率域比较，避免数值抖动）
        abs_threshold_power = 10.0 ** ((-70.0 + 0.691) / 10.0)
        abs_mask = z_arr > abs_threshold_power

        if not np.any(abs_mask):
            return -np.inf, blocks_loudness

        # Step 3: 相对门限 = 通过绝对门限的块的平均响度 - 10 LU
        # 功率域等效：mean(z_abs) / 10.0
        mean_z_abs = np.mean(z_arr[abs_mask])
        rel_threshold_power = mean_z_abs / 10.0

        # Step 4: 双门限筛选
        final_mask = z_arr > rel_threshold_power
        if not np.any(final_mask):
            return -np.inf, blocks_loudness

        # Step 5: 集成响度 = 通过双门限的块的平均 z 转 dB
        mean_z_final = np.mean(z_arr[final_mask])
        integrated = -0.691 + 10.0 * np.log10(mean_z_final)

        return float(integrated), blocks_loudness

    def _momentary_short_term(self, filtered: np.ndarray,
                              callback: Optional[Callable] = None):
        """
        Momentary / Short-term（EBU Tech 3341）
        返回: (current_momentary, current_short_term,
               max_momentary, max_short_term, short_term_values)
        """
        sr = 48000
        win_100ms = int(0.1 * sr)   # 4800 samples
        num_samples = len(filtered)

        # 计算所有 100ms 窗口的加权功率（步进 100ms，无重叠）
        num_100ms = max(0, (num_samples - win_100ms) // win_100ms + 1)
        weighted_powers = []

        report_interval = max(1, num_100ms // 10)

        for i in range(num_100ms):
            start = i * win_100ms
            end = start + win_100ms
            block = filtered[start:end]
            z = self._weighted_power(block)
            weighted_powers.append(z)

            if callback and (i + 1) % report_interval == 0:
                pct = 50.0 + (i + 1) / num_100ms * 30.0  # 占 50~80%
                self._cb(callback, "计算短时/瞬时响度", pct)

        if not weighted_powers:
            return -np.inf, -np.inf, -np.inf, -np.inf, []

        # Momentary: 400ms 滑动窗口 = 4 个 100ms
        m_win = 4
        momentary_values = []
        for i in range(len(weighted_powers)):
            start = max(0, i - m_win + 1)
            window = weighted_powers[start:i + 1]
            if len(window) < m_win:
                continue  # 窗口未满，按标准不输出
            mean_z = np.mean(window)
            if mean_z > 0.0:
                m = -0.691 + 10.0 * np.log10(mean_z)
            else:
                m = -np.inf
            momentary_values.append(m)

        # Short-term: 3s 滑动窗口 = 30 个 100ms
        s_win = 30
        short_term_values = []
        for i in range(len(weighted_powers)):
            start = max(0, i - s_win + 1)
            window = weighted_powers[start:i + 1]
            if len(window) < s_win:
                continue
            mean_z = np.mean(window)
            if mean_z > 0.0:
                s = -0.691 + 10.0 * np.log10(mean_z)
            else:
                s = -np.inf
            short_term_values.append(s)

        max_momentary = max(momentary_values) if momentary_values else -np.inf
        max_short_term = max(short_term_values) if short_term_values else -np.inf
        current_momentary = momentary_values[-1] if momentary_values else -np.inf
        current_short_term = short_term_values[-1] if short_term_values else -np.inf

        return (current_momentary, current_short_term,
                max_momentary, max_short_term, short_term_values)

    @staticmethod
    def _lra(short_term_values: List[float]) -> float:
        """响度范围 LRA（EBU Tech 3342）"""
        if not short_term_values:
            return 0.0

        st_arr = np.array(short_term_values, dtype=np.float64)

        # 第一门限：-70.0 LUFS
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

    def process_audio(self, audio: np.ndarray, sr: Optional[int] = None,
                      progress_callback: Optional[Callable] = None) -> dict:
        """
        处理完整音频并返回测量结果。

        Args:
            audio: 音频数据，shape 为 (samples,) 或 (samples, channels)
            sr: 原始采样率。若非 48000，会先重采样到 48000。
            progress_callback: 进度回调，签名为 (step_name, overall_progress_pct)
                               step_name 为当前步骤描述（中文）
                               overall_progress_pct 为 0.0~100.0 的浮点数

        Returns:
            dict，包含以下字段（与 main_gui.py 兼容）：
                integrated: float      # 集成响度 LUFS
                short_term: float      # 当前/最后短时响度 LUFS
                momentary: float       # 当前/最后瞬时响度 LUFS
                true_peak: float       # 最大真峰值 dBTP
                lra: float             # 响度范围 LU
                max_short_term: float  # 最大短时响度
                max_momentary: float   # 最大瞬时响度
                blocks: List[float]    # 400ms 块响度序列（LUFS）
        """
        # 标准化输入维度
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        audio = np.asarray(audio, dtype=np.float64)

        actual_sr = sr if sr is not None else self.sample_rate

        # ---- 阶段 1: 重采样到 48kHz ----
        if actual_sr != 48000:
            self._cb(progress_callback, "重采样到 48kHz", 0.0)
            audio = self._resample_to_48k(audio, actual_sr, progress_callback)

        # ---- 阶段 2: K-加权滤波 ----
        self._cb(progress_callback, "K-加权滤波", 15.0)
        filtered = self._k_weight(audio)
        self._cb(progress_callback, "K-加权滤波", 20.0)

        # ---- 阶段 3: 真峰值 ----
        self._cb(progress_callback, "计算真峰值", 20.0)
        true_peak_db = self._true_peak(audio, progress_callback)

        # ---- 阶段 4: 集成响度 ----
        self._cb(progress_callback, "计算集成响度", 25.0)
        integrated, blocks_loudness = self._integrated_loudness(
            filtered, progress_callback
        )

        # ---- 阶段 5: Momentary / Short-term ----
        self._cb(progress_callback, "计算短时/瞬时响度", 50.0)
        (current_momentary, current_short_term,
         max_momentary, max_short_term, short_term_values) = \
            self._momentary_short_term(filtered, progress_callback)

        # ---- 阶段 6: LRA ----
        self._cb(progress_callback, "计算响度范围", 80.0)
        lra = self._lra(short_term_values)
        self._cb(progress_callback, "计算响度范围", 90.0)

        # ---- 收尾 ----
        self._cb(progress_callback, "整理结果", 95.0)
        result = {
            'integrated': integrated,
            'short_term': current_short_term,
            'momentary': current_momentary,
            'true_peak': true_peak_db,
            'lra': lra,
            'max_short_term': max_short_term,
            'max_momentary': max_momentary,
            'blocks': blocks_loudness,
        }
        self._cb(progress_callback, "测量完成", 100.0)
        return result
