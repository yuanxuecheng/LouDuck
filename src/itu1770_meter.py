"""
ITU-R BS.1770-5 响度测量核心算法 (整合修复版)
支持沉浸式音频 (5.1.4, 7.1.4, 22.2)
修复：
- process_audio 变量定义错误
- 最大值追踪（max_momentary, max_short_term）
"""

import numpy as np
from scipy import signal
from dataclasses import dataclass
from typing import List, Optional
from collections import deque


@dataclass
class ChannelConfig:
    """声道配置"""
    name: str
    azimuth: float
    elevation: float
    is_lfe: bool = False
    
    def get_weight(self) -> float:
        """ITU-R BS.1770-5 Table 4 权重计算"""
        if self.is_lfe:
            return 0.0
        
        abs_azimuth = abs(self.azimuth)
        abs_elevation = abs(self.elevation)
        
        # 仰角 >= 30°
        if abs_elevation >= 30:
            return 1.0
        
        # 仰角 < 30°，根据方位角
        if abs_azimuth < 60:
            return 1.0
        elif 60 <= abs_azimuth <= 120:
            return 1.41  # +1.5 dB
        else:
            return 1.0


class ITU1770Meter:
    """ITU-R BS.1770-5 响度计"""
    
    # 48kHz 标准滤波器系数 (ITU-R BS.1770-5 Table 1/2)
    STAGE1_B = [1.53512485958697, -2.69169618940638, 1.19839281085285]
    STAGE1_A = [1.0, -1.69065929318241, 0.73248077421585]
    STAGE2_B = [1.0, -2.0, 1.0]
    STAGE2_A = [1.0, -1.99004745483398, 0.99007225036621]
    
    # 真峰值 FIR 系数 (ITU-R BS.1770-5 Annex 2, 48阶4相)
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
    ])
    
    # 标准配置
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
        self.block_samples = int(0.4 * sample_rate)  # 400ms 块大小
        self.weights = [ch.get_weight() for ch in channel_config]
        
        # 历史记录长度
        self.short_term_blocks = int(3.0 / 0.4)  # 3秒 = 7.5个块，取整为8
        
        # 滑动窗口参数（REAPER 风格）
        self.update_interval = int(0.1 * sample_rate)  # 100ms
        self.m_win_cnt = int(0.4 / 0.1)  # 400ms / 100ms = 4
        self.s_win_cnt = int(3.0 / 0.1)  # 3s / 100ms = 30
        
        self.reset()
    
    def reset(self):
        """重置状态"""
        self.zi1 = None
        self.zi2 = None
        self.loudness_blocks = []
        self.block_powers = []  # 存储各声道原始 mean_sq，用于标准集成响度计算
        self.block_buffer = []
        self.true_peak_max = -np.inf
        self.short_term_history = deque(maxlen=self.short_term_blocks)
        self.momentary_history = deque(maxlen=10)
        # 追踪最大响度值
        self.max_momentary = -np.inf
        self.max_short_term = -np.inf
        
        # 滑动窗口状态（REAPER 风格）
        self.m_buf = []  # 400ms 功率缓冲区（4 个 100ms）
        self.s_buf = []  # 3s 功率缓冲区（30 个 100ms）
        self.win_pos = 0  # 当前 100ms 窗口位置

    
    @classmethod
    def auto_config(cls, num_channels: int) -> List[ChannelConfig]:
        """自动检测配置"""
        mapping = {2: 'stereo', 6: '5.1', 8: '7.1', 10: '5.1.4', 12: '7.1.4'}
        config_name = mapping.get(num_channels, 'stereo')
        return cls.CONFIGS.get(config_name, cls.CONFIGS['stereo'])
    
    def apply_k_weighting(self, audio: np.ndarray) -> np.ndarray:
        """K-加权滤波"""
        num_ch = audio.shape[1] if audio.ndim > 1 else 1
        
        if self.zi1 is None or self.zi1.shape[1] != num_ch:
            self.zi1 = np.zeros((2, num_ch))
        if self.zi2 is None or self.zi2.shape[1] != num_ch:
            self.zi2 = np.zeros((2, num_ch))
        
        y1, self.zi1 = signal.lfilter(self.STAGE1_B, self.STAGE1_A, audio, axis=0, zi=self.zi1)
        y2, self.zi2 = signal.lfilter(self.STAGE2_B, self.STAGE2_A, y1, axis=0, zi=self.zi2)
        return y2
    
    def calculate_true_peak(self, audio: np.ndarray) -> float:
        """真峰值测量 (4x 过采样)"""
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        
        max_tp = -np.inf
        for ch in range(audio.shape[1]):
            x = audio[:, ch]
            x_up = np.zeros(len(x) * 4)
            x_up[::4] = x
            y = signal.lfilter(self.TP_FIR, 1.0, x_up)
            tp = np.max(np.abs(y))
            max_tp = max(max_tp, tp)
        
        tp_db = 20 * np.log10(max_tp) if max_tp > 0 else -np.inf
        self.true_peak_max = max(self.true_peak_max, tp_db)
        return tp_db
    
    def get_true_peak_max(self) -> float:
        """获取整个测量的最大真峰值"""
        return self.true_peak_max if self.true_peak_max != -np.inf else -np.inf
    
    def process_block(self, audio: np.ndarray) -> float:
        """处理单个响度块 - 包含 K-加权"""
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        
        filtered = self.apply_k_weighting(audio)
        return self.process_filtered_block(filtered)

    
    def process_filtered_block(self, filtered: np.ndarray) -> float:
        """处理已滤波的响度块 - 跳过 K-加权"""
        if filtered.ndim == 1:
            filtered = filtered.reshape(-1, 1)
        
        # 计算各声道 mean_sq（原有逻辑，去掉 K-加权部分）
        channel_powers = []
        for i, (ch_cfg, weight) in enumerate(zip(self.channel_config, self.weights)):
            if ch_cfg.is_lfe or i >= filtered.shape[1]:
                continue
            if weight > 0:
                mean_sq = np.mean(filtered[:, i] ** 2)
                channel_powers.append((weight, mean_sq))
        
        self.block_powers.append(channel_powers)
        
        weighted_sum = sum(w * msq for w, msq in channel_powers)
        valid_channels = len(channel_powers)
        
        if weighted_sum > 0 and valid_channels > 0:
            loudness = -0.691 + 10 * np.log10(weighted_sum)
        else:
            loudness = -np.inf
        
        self.loudness_blocks.append(loudness)
        self.short_term_history.append(loudness)
        self.momentary_history.append(loudness)
        
        return loudness

    
    def process_100ms_window(self, filtered: np.ndarray) -> float:
        """处理 100ms 窗口，更新滑动窗口（REAPER 风格）"""
        if filtered.ndim == 1:
            filtered = filtered.reshape(-1, 1)
        
        # 计算各声道功率和（不是 mean_sq）
        channel_powers = []
        total_power = 0.0
        for i, (ch_cfg, weight) in enumerate(zip(self.channel_config, self.weights)):
            if ch_cfg.is_lfe or i >= filtered.shape[1]:
                continue
            if weight > 0:
                power = np.sum(filtered[:, i] ** 2)      # 功率和（用于滑动窗口）
                mean_sq = power / len(filtered)           # mean_sq（用于集成响度）
                channel_powers.append((weight, mean_sq))  # 保存 mean_sq
                total_power += weight * power
        
        # 保存原始功率值（用于标准集成响度计算）
        self.block_powers.append(channel_powers)
        
        # 更新 400ms 滑动窗口
        self.m_buf.append(total_power)
        if len(self.m_buf) > self.m_win_cnt:
            self.m_buf.pop(0)
        
        # 更新 3s 滑动窗口
        self.s_buf.append(total_power)
        if len(self.s_buf) > self.s_win_cnt:
            self.s_buf.pop(0)
        
        # 计算 Momentary（400ms）
        if len(self.m_buf) >= self.m_win_cnt:
            m_total = sum(self.m_buf)
            m_samples = self.m_win_cnt * len(filtered)
            m_mean = m_total / m_samples
            if m_mean > 0:
                momentary = -0.691 + 10 * np.log10(m_mean)
            else:
                momentary = -np.inf
        else:
            momentary = -np.inf
        
        # 计算 Short-term（3s）
        if len(self.s_buf) >= self.s_win_cnt:
            s_total = sum(self.s_buf)
            s_samples = self.s_win_cnt * len(filtered)
            s_mean = s_total / s_samples
            if s_mean > 0:
                short_term = -0.691 + 10 * np.log10(s_mean)
            else:
                short_term = -np.inf
        else:
            short_term = -np.inf
        
        # 保存到历史记录
        if momentary > -np.inf:
            self.loudness_blocks.append(momentary)
            self.momentary_history.append(momentary)
        if short_term > -np.inf:
            self.short_term_history.append(short_term)
        
        return momentary
    
    def get_integrated_loudness(self) -> float:
        """计算集成响度（标准 ITU-R BS.1770-3 顺序）"""
        if not self.block_powers:
            return -np.inf
        
        # Step 1: 计算每个块的响度（用于门控）
        block_loudness = []
        for ch_powers in self.block_powers:
            weighted_sum = sum(w * msq for w, msq in ch_powers)
            if weighted_sum > 0:
                loudness = -0.691 + 10 * np.log10(weighted_sum)
            else:
                loudness = -np.inf
            block_loudness.append(loudness)
        
        blocks = np.array(block_loudness)
        
        # Step 2: 绝对门限 -70 LUFS
        valid_mask = blocks > -70
        if not np.any(valid_mask):
            return -np.inf
        
        # Step 3: 关键修正！相对门限 = log(mean(mean_sq)) - 10（REAPER 风格）
        # 先计算所有通过绝对门限块的平均功率（不是平均响度）
        valid_powers = []
        for i, is_valid in enumerate(valid_mask):
            if is_valid:
                weighted_sum = sum(w * msq for w, msq in self.block_powers[i])
                valid_powers.append(weighted_sum)
        
        avg_power = np.mean(valid_powers)
        avg_loudness = -0.691 + 10 * np.log10(avg_power)
        relative_threshold = avg_loudness - 10
        
        # Step 4: 最终门限
        final_mask = blocks > relative_threshold
        if not np.any(final_mask):
            return -np.inf
        
        # Step 5: 标准顺序 - 先对各声道 power 取平均，再加权求和
        weighted_mean_powers = []
        for ch_idx in range(len(self.channel_config)):
            if self.channel_config[ch_idx].is_lfe:
                continue
            
            ch_powers_final = []
            for i, is_final in enumerate(final_mask):
                if is_final and ch_idx < len(self.block_powers[i]):
                    ch_powers_final.append(self.block_powers[i][ch_idx][1])
            
            if ch_powers_final:
                mean_power = np.mean(ch_powers_final)
                weight = self.channel_config[ch_idx].get_weight()
                weighted_mean_powers.append(weight * mean_power)
        
        total_weighted_power = sum(weighted_mean_powers)
        if total_weighted_power <= 0:
            return -np.inf
        
        return float(-0.691 + 10 * np.log10(total_weighted_power))


    
    def get_short_term_loudness(self) -> float:
        """获取短期响度 (3秒滑动窗口)"""
        if not self.short_term_history:
            return -np.inf
        return float(np.mean(self.short_term_history))
    
    def get_momentary_loudness(self) -> float:
        """获取瞬时响度 (400ms)"""
        if not self.momentary_history:
            return -np.inf
#       if len(self.momentary_history) >= 3:
#           return float(np.mean(list(self.momentary_history)[-3:]))
        return float(self.momentary_history[-1])
    
    def get_loudness_range(self) -> float:
        """计算响度范围 LRA（EBU Tech 3342）
        
        使用 3秒短期响度，双门限：-70 LUFS 绝对，avg - 20 dB 相对
        """
        if not self.short_term_history or len(self.short_term_history) < 2:
            return 0.0
        
        # 使用短期响度历史（3秒窗口）
        st_blocks = np.array(self.short_term_history)
        
        # 第一门限：-70 LUFS
        valid = st_blocks[st_blocks > -70]
        if len(valid) < 2:
            return 0.0
        
        # 第二门限：平均值 - 20 dB（EBU Tech 3342）
        avg = np.mean(valid)
        second_gate = avg - 20
        
        # 应用第二门限
        gated = valid[valid > second_gate]
        if len(gated) < 2:
            return 0.0
        
        # 计算 10% 和 95% 分位数
        p10 = np.percentile(gated, 10)
        p95 = np.percentile(gated, 95)
        
        return float(max(0, p95 - p10))

    
    def process_audio(self, audio: np.ndarray, sr: Optional[int] = None, 
                     progress_callback=None) -> dict:
        """处理完整音频，支持进度回调
        
        Args:
            audio: 音频数据
            sr: 采样率（如需重采样）
            progress_callback: 进度回调函数，接收 (processed_blocks, total_blocks)
        """
        # 先处理采样率
        if sr and sr != self.sample_rate:
            from scipy import signal as sp_signal
            num_samples = int(len(audio) * self.sample_rate / sr)
            audio = sp_signal.resample(audio, num_samples)
        
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        
        num_samples = len(audio)
        
        # 滑动窗口参数
        win_len = self.update_interval  # 100ms
        total_windows = max(1, (num_samples - win_len) // win_len + 1)
        
        # 关键：先对整个音频连续应用 K-加权（只做一次！）
        # 重置滤波器状态，确保从头开始
        self.zi1 = None
        self.zi2 = None
        filtered_audio = self.apply_k_weighting(audio)
        
        # 使用滑动窗口（REAPER 风格）
        # 每 100ms 计算一次
        for win_idx, i in enumerate(range(0, num_samples - win_len + 1, win_len)):
            block = filtered_audio[i:i + win_len]
            
            # 处理 100ms 窗口，更新滑动窗口
            loudness = self.process_100ms_window(block)
            
            # 真峰值使用原始音频（未滤波）
            self.calculate_true_peak(audio[i:i + win_len])
            
            # 更新最大瞬时响度
            if loudness > -np.inf:
                self.max_momentary = max(self.max_momentary, loudness)
            
            # 更新最大短期响度
            if len(self.short_term_history) >= 3:
                current_short_term = np.mean(self.short_term_history)
                self.max_short_term = max(self.max_short_term, current_short_term)
            
            # 报告进度
            if progress_callback and (win_idx % 10 == 0 or win_idx == total_windows - 1):
                progress_callback(win_idx + 1, total_windows)

        
        # 返回结果
        return {
            'integrated': self.get_integrated_loudness(),
            'short_term': self.get_short_term_loudness(),
            'momentary': self.get_momentary_loudness(),
            'true_peak': self.get_true_peak_max(),
            'lra': self.get_loudness_range(),
            'max_true_peak': self.get_true_peak_max(),
            'max_momentary': self.max_momentary,
            'max_short_term': self.max_short_term,
            'blocks': list(self.loudness_blocks)
        }

