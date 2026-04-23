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
        
        self.reset()
    
    def reset(self):
        """重置状态"""
        self.zi1 = None
        self.zi2 = None
        self.loudness_blocks = []
        self.block_buffer = []
        self.true_peak_max = -np.inf
        self.short_term_history = deque(maxlen=self.short_term_blocks)
        self.momentary_history = deque(maxlen=10)
        # 追踪最大响度值
        self.max_momentary = -np.inf
        self.max_short_term = -np.inf
    
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
        """处理单个响度块 (400ms)"""
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        
        # 应用 K-加权
        filtered = self.apply_k_weighting(audio)
        
        # 计算加权均方值
        weighted_sum = 0.0
        valid_channels = 0
        
        for i, (ch_cfg, weight) in enumerate(zip(self.channel_config, self.weights)):
            if ch_cfg.is_lfe or i >= filtered.shape[1]:
                continue
            if weight > 0:
                mean_sq = np.mean(filtered[:, i] ** 2)
                weighted_sum += weight * mean_sq
                valid_channels += 1
        
        # 计算响度
        if weighted_sum > 0 and valid_channels > 0:
            loudness = -0.691 + 10 * np.log10(weighted_sum)
        else:
            loudness = -np.inf
        
        # 保存到历史记录
        self.loudness_blocks.append(loudness)
        self.short_term_history.append(loudness)
        self.momentary_history.append(loudness)
        
        return loudness
    
    def get_integrated_loudness(self) -> float:
        """计算双门控集成响度"""
        if not self.loudness_blocks:
            return -np.inf
        
        blocks = np.array(self.loudness_blocks)
        
        # 绝对门限 -70 LUFS
        valid = blocks[blocks > -70]
        if len(valid) == 0:
            return -np.inf
        
        # 相对门限：平均值 - 10 LU
        avg = np.mean(valid)
        relative_threshold = avg - 10
        
        # 最终门限应用
        final = valid[valid > relative_threshold]
        
        if len(final) == 0:
            return -np.inf
        
        return float(np.mean(final))
    
    def get_short_term_loudness(self) -> float:
        """获取短期响度 (3秒滑动窗口)"""
        if not self.short_term_history:
            return -np.inf
        return float(np.mean(self.short_term_history))
    
    def get_momentary_loudness(self) -> float:
        """获取瞬时响度 (400ms)"""
        if not self.momentary_history:
            return -np.inf
        if len(self.momentary_history) >= 3:
            return float(np.mean(list(self.momentary_history)[-3:]))
        return float(self.momentary_history[-1])
    
    def get_loudness_range(self) -> float:
        """计算响度范围 (LRA)"""
        if len(self.loudness_blocks) < 2:
            return 0.0
        
        blocks = np.array([b for b in self.loudness_blocks if b > -70])
        if len(blocks) < 2:
            return 0.0
        
        p10 = np.percentile(blocks, 10)
        p95 = np.percentile(blocks, 95)
        lra = p95 - p10
        
        return float(max(0, lra))
    
    def process_audio(self, audio: np.ndarray, sr: Optional[int] = None, 
                     progress_callback=None) -> dict:
        """处理完整音频，支持进度回调
        
        Args:
            audio: 音频数据
            sr: 采样率（如需重采样）
            progress_callback: 进度回调函数，接收 (processed_blocks, total_blocks)
        """
        if sr and sr != self.sample_rate:
            from scipy import signal as sp_signal
            num_samples = int(len(audio) * self.sample_rate / sr)
            audio = sp_signal.resample(audio, num_samples)
        
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        
        num_samples = len(audio)
        hop = int(self.block_samples * 0.25)  # 75% 重叠
        
        # 计算总块数用于进度
        total_blocks = max(1, (num_samples - self.block_samples) // hop + 1)
        
        # 处理所有块
        for block_idx, i in enumerate(range(0, num_samples - self.block_samples + 1, hop)):
            block = audio[i:i + self.block_samples]
            
            # 处理块
            loudness = self.process_block(block)
            
            # 更新真峰值
            self.calculate_true_peak(block)
            
            # 更新最大瞬时响度
            self.max_momentary = max(self.max_momentary, loudness)
            
            # 更新最大短期响度
            if len(self.short_term_history) >= 3:
                current_short_term = np.mean(self.short_term_history)
                self.max_short_term = max(self.max_short_term, current_short_term)
            
            # 报告进度（每10个块或最后一块）
            if progress_callback and (block_idx % 10 == 0 or block_idx == total_blocks - 1):
                progress_callback(block_idx + 1, total_blocks)
        
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
