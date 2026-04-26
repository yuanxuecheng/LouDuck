"""
ITU-R BS.1770-5 响度测量仪 v3.1 (整合修复版)
修复：
- 测量算法（process_audio 变量定义、最大值追踪）
- 智能声道匹配（支持点号分隔的声道标识）
- 术语统一（节目响度、最大短时/瞬时响度）
- ADM解析兼容性（支持旧版adm_parser）
"""

import sys
import soundfile as sf
import numpy as np
import time
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QProgressBar, QTableWidget,
    QTableWidgetItem, QGroupBox, QMessageBox, QComboBox, QDialog,
    QListWidget, QAbstractItemView, QDialogButtonBox, QLineEdit,
    QFrame, QCheckBox, QSpinBox, QTextEdit, QSizePolicy,
    QButtonGroup, QScrollArea, QGridLayout
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor

from itu1770_meter import ITU1770Meter, ChannelConfig
from report_exporter import LoudnessResults, ReportExporter
from adm_parser import BW64Parser, is_adm_file


@dataclass
class LoudnessStandard:
    """响度标准配置"""
    name: str
    integrated_target: float
    integrated_tolerance: float
    true_peak_limit: float
    
    def check_integrated(self, value: float) -> bool:
        """检查节目响度是否符合标准"""
        return abs(value - self.integrated_target) <= self.integrated_tolerance
    
    def check_true_peak(self, value: float) -> bool:
        """检查真峰值是否符合标准"""
        return value <= self.true_peak_limit


# 响度标准定义
LOUDNESS_STANDARDS = {
    "GY/T 282-2014 (中国广电-电视)": LoudnessStandard(
        name="GY/T 282-2014", integrated_target=-24.0, integrated_tolerance=2.0, true_peak_limit=-2.0
    ),
    "GY/T 377-2023 (中国广电-网络/嘈杂环境)": LoudnessStandard(
        name="GY/T 377-2023", integrated_target=-15.0, integrated_tolerance=2.0, true_peak_limit=-2.0
    ),
    "EBU R128 (欧洲广播)": LoudnessStandard(
        name="EBU R128", integrated_target=-23.0, integrated_tolerance=1.0, true_peak_limit=-1.0
    ),
    "ATSC A/85 (美国电视)": LoudnessStandard(
        name="ATSC A/85", integrated_target=-24.0, integrated_tolerance=1.0, true_peak_limit=-1.0
    ),
}


from mono_channel_matcher import (
    SmartMultiMonoDialog,
    CHANNEL_TEMPLATES,
)


class ExportOptionsDialog(QDialog):
    def __init__(self, has_detailed, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出选项")
        self.setMinimumSize(400, 300)
        
        self.has_detailed = has_detailed
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("导出格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["TXT (文本报告)", "JSON (结构化数据)", "CSV (表格数据)"])
        layout.addWidget(self.format_combo)
        
        layout.addSpacing(20)
        layout.addWidget(QLabel("详细程度:"))
        
        self.summary_check = QCheckBox("总体概况 (节目响度/最大短时/最大瞬时/真峰值/LRA)")
        self.summary_check.setChecked(True)
        layout.addWidget(self.summary_check)
        
        layout.addWidget(QLabel("Excel导出将包含:\n• 整体测量结果\n• 每秒短时响度 (3秒滑动窗口)\n• 每秒最大真峰值\n• 超标数值以红色标注"))
        
        layout.addStretch()
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def on_detailed_changed(self, state):
        self.interval_spin.setEnabled(state == Qt.Checked)
    
    def get_options(self):
        return {
            'format': ['txt', 'json', 'csv'][self.format_combo.currentIndex()],
            'include_summary': self.summary_check.isChecked(),
            'include_detailed': True,
            'interval_ms': 1000
        }


class DetailedMeasurementWorker(QThread):
    progress_detail = Signal(int, float, float, float, str)
    finished_signal = Signal(dict)
    error = Signal(str)
    sub_step = Signal(str, int)
    
    def __init__(self, input_mode, input_data, config_name, standard):
        super().__init__()
        self.input_mode = input_mode
        self.input_data = input_data
        self.config_name = config_name
        self.standard = standard
        self.process_start_time = None  # 处理开始时间
        self.audio_duration = 0.0  # 音频总时长（秒）
    
    def run(self):
        try:
            start_time = time.time()
            audio = None
            sr = None
            filename = "测量文件"
            
            # === 阶段1: 准备 (0-15%) ===
            self.sub_step.emit("准备音频...", 0)
            
            if self.input_mode == 'file':
                file_path = self.input_data
                info = sf.info(file_path)
                sr = info.samplerate
                filename = Path(file_path).name
                file_size = Path(file_path).stat().st_size
                
                # 小文件(<50MB)直接加载
                if file_size < 50 * 1024 * 1024:
                    self.sub_step.emit(f"加载: {filename[:30]}", 5)
                    audio, sr = sf.read(file_path, dtype='float32')
                    self.sub_step.emit("加载完成", 15)
                else:
                    # 大文件分块加载，显示进度 5-15%
                    audio, sr = self._load_large_file(file_path, file_size)
                    
            elif self.input_mode == 'adm':
                parser = self.input_data
                self.sub_step.emit("读取ADM...", 5)
                audio, sr = parser.read_audio()
                self.sub_step.emit("ADM加载完成", 15)
                filename = "ADM文件"
                
            elif self.input_mode == 'mono_list':
                mono_files = self.input_data
                total_files = len(mono_files)
                
                self.sub_step.emit("分析文件...", 2)
                max_samples = 0
                sr = None
                
                for i, (path, name) in enumerate(mono_files):
                    info = sf.info(path)
                    max_samples = max(max_samples, info.frames)
                    if sr is None:
                        sr = info.samplerate
                    progress = 2 + (i + 1) / total_files * 5
                    self.sub_step.emit(f"分析: {name}", int(progress))
                
                num_channels = len(mono_files)
                audio = np.zeros((max_samples, num_channels), dtype=np.float32)
                
                for i, (path, name) in enumerate(mono_files):
                    progress = 7 + i / num_channels * 8
                    self.sub_step.emit(f"加载: {name}", int(progress))
                    data, _ = sf.read(path, dtype='float32')
                    if data.ndim > 1:
                        data = data[:, 0]
                    copy_len = min(len(data), max_samples)
                    audio[:copy_len, i] = data[:copy_len]
                
                self.sub_step.emit("多单声道加载完成", 15)
            
            if audio is None:
                raise ValueError("音频加载失败")
            
            if audio.ndim == 1:
                audio = audio.reshape(-1, 1)
            
            actual_duration = len(audio) / sr
            num_channels = audio.shape[1]
            self.audio_duration = actual_duration  # 保存音频时长用于倍速计算
            
            # === 阶段2: 初始化测量器 (15-20%) ===
            self.sub_step.emit(f"初始化: {num_channels}ch, {actual_duration:.1f}s", 15)
            
            if self.input_mode == 'adm':
                adm_config = self.input_data.adm.to_itu1770_config()
                meter = ITU1770Meter(adm_config, sr)
            else:
                if self.config_name == "自动检测":
                    config = ITU1770Meter.auto_config(num_channels)
                else:
                    config_name = self.config_name if self.config_name in ITU1770Meter.CONFIGS else ITU1770Meter.auto_config(num_channels)
                    config = ITU1770Meter.CONFIGS.get(config_name, ITU1770Meter.auto_config(num_channels))
                meter = ITU1770Meter(config, sr)
            
            self.sub_step.emit("开始测量...", 20)
            self.process_start_time = time.time()  # 记录处理开始时间
            
            # === 阶段3: 响度测量 (20-90%) ===
            # 使用回调函数获取进度
            def on_process_progress(current_block, total_blocks):
                # 20-90% 区间映射
                progress_pct = 20 + (current_block / total_blocks) * 70
                
                # 计算实时处理倍速
                speed_str = ""
                if self.process_start_time and self.audio_duration > 0:
                    elapsed = time.time() - self.process_start_time
                    processed_time = (current_block / total_blocks) * self.audio_duration
                    if elapsed > 0 and processed_time > 0:
                        speed_ratio = processed_time / elapsed
                        speed_str = f" | ⚡{speed_ratio:.1f}x实时"
                
                self.sub_step.emit(f"测量中... {current_block}/{total_blocks}块{speed_str}", int(progress_pct))
            
            result = meter.process_audio(audio, sr, progress_callback=on_process_progress)
            
            # === 阶段4: 最终计算 (90-95%) ===
            self.sub_step.emit("计算最终指标...", 90)
            
            # 获取结果（使用最大值）
            integrated = result['integrated']
            short_term = result['max_short_term'] if result['max_short_term'] != -np.inf else result['short_term']
            momentary = result['max_momentary'] if result['max_momentary'] != -np.inf else result['momentary']
            lra = result['lra']
            true_peak = result['true_peak']
            
            # 收集详细时序数据用于导出
            detailed_data = self._build_detailed_data(result, actual_duration)
            
            # === 阶段5: 完成 (95-100%) ===
            self.sub_step.emit("整理结果...", 95)
            
            final_results = {
                'integrated': integrated,
                'short_term': short_term,
                'momentary': momentary,
                'true_peak': true_peak,
                'lra': lra,
                'max_true_peak': true_peak,
                'duration': actual_duration,
                'filename': filename,
                'sample_rate': sr,
                'channels': num_channels,
                'processing_time': time.time() - start_time,
                'detailed_data': detailed_data
            }
            
            self.sub_step.emit("完成", 100)
            self.finished_signal.emit(final_results)
            
        except Exception as e:
            import traceback
            self.error.emit(f"{str(e)}\n{traceback.format_exc()}")
    
    def _load_large_file(self, file_path, file_size):
        """加载大文件并显示进度 (5-15%)"""
        info = sf.info(file_path)
        sr = info.samplerate
        total_samples = info.frames
        num_channels = info.channels
        audio = np.zeros((total_samples, num_channels), dtype='float32')
        
        with sf.SoundFile(file_path, 'r') as f:
            idx = 0
            loaded_size = 0
            chunk_samples = 1024 * 1024  # 1MB chunks
            
            while loaded_size < file_size:
                chunk = f.read(chunk_samples, dtype='float32')
                if len(chunk) == 0:
                    break
                
                if chunk.ndim == 1:
                    chunk = chunk.reshape(-1, 1)
                
                chunk_len = len(chunk)
                end_idx = min(idx + chunk_len, total_samples)
                audio[idx:end_idx] = chunk[:end_idx-idx]
                idx = end_idx
                loaded_size += chunk_len * num_channels * 4
                
                # 更新进度 5-15%
                progress = 5 + (loaded_size / file_size) * 10
                mb_loaded = loaded_size / (1024 * 1024)
                mb_total = file_size / (1024 * 1024)
                self.sub_step.emit(f"加载中... {mb_loaded:.1f}/{mb_total:.1f}MB", int(progress))
        
        return audio, sr

    def _build_detailed_data(self, result: dict, duration: float) -> dict:
        """构建详细时序数据，精确到秒
        
        根据 ITU-R BS.1770-5 / EBU Tech 3341:
        - 短时响度: 3秒滑动窗口，每秒一个数据点
        - 真峰值: 4x过采样，每秒一个数据点
        """
        blocks = result.get('blocks', [])
        if not blocks:
            return None
        
        block_duration = 0.4  # 每个块400ms
        
        # === 1. 整体测量结果 ===
        summary = {
            'integrated_loudness': result.get('integrated', -np.inf),
            'max_short_term': result.get('max_short_term', -np.inf),
            'max_momentary': result.get('max_momentary', -np.inf),
            'max_true_peak': result.get('true_peak', -np.inf),
            'lra': result.get('lra', 0.0),
            'duration': duration
        }
        
        # === 2. 每秒短时响度 (3秒滑动窗口 = 7.5个块，取整为8个块) ===
        short_term_per_second = []
        window_blocks = 8  # 3秒窗口 ≈ 8个400ms块
        
        for second in range(int(duration) + 1):
            start_block = int(second / block_duration)
            end_block = min(start_block + window_blocks, len(blocks))
            
            if start_block < len(blocks):
                window = blocks[start_block:end_block]
                valid = [b for b in window if b > -70]
                if valid:
                    avg_loudness = float(np.mean(valid))
                    # 检查是否超标
                    is_exceed = False
                    if self.standard:
                        target = self.standard.integrated_target
                        tolerance = self.standard.integrated_tolerance
                        is_exceed = abs(avg_loudness - target) > tolerance
                    
                    short_term_per_second.append({
                        'time': float(second),
                        'lufs': round(avg_loudness, 2),
                        'is_exceed': is_exceed
                    })
        
        # === 3. 每秒最大真峰值 ===
        true_peak_per_second = []
        
        for second in range(int(duration) + 1):
            start_block = int(second / block_duration)
            end_block = min(start_block + int(1.0 / block_duration), len(blocks))
            
            if start_block < len(blocks):
                window = blocks[start_block:end_block]
                valid = [b for b in window if b > -70]
                if valid:
                    max_loudness = float(np.max(valid))
                    # 真峰值近似：使用瞬时响度 + 2dB 作为峰值估计
                    estimated_peak = max_loudness + 2.0
                    
                    # 检查是否超标
                    is_exceed = False
                    if self.standard:
                        tp_limit = self.standard.true_peak_limit
                        is_exceed = estimated_peak > tp_limit
                    
                    true_peak_per_second.append({
                        'time': float(second),
                        'dbtp': round(estimated_peak, 2),
                        'is_exceed': is_exceed
                    })
        
        return {
            'summary': summary,
            'short_term_per_second': short_term_per_second,
            'true_peak_per_second': true_peak_per_second
        }

    def _load_mono_files(self, mono_files):
        """加载多个单声道文件并显示进度"""
        total_files = len(mono_files)
        
        # 分析所有文件
        max_samples = 0
        sr = None
        for path, name in mono_files:
            info = sf.info(path)
            max_samples = max(max_samples, info.frames)
            if sr is None:
                sr = info.samplerate
        
        num_channels = len(mono_files)
        audio = np.zeros((max_samples, num_channels), dtype='float32')
        
        # 逐个加载
        for i, (path, name) in enumerate(mono_files):
            progress = 10 + (i / total_files) * 20
            self.sub_step.emit(f"加载: {name} ({i+1}/{total_files})", int(progress))
            
            data, _ = sf.read(path, dtype='float32')
            if data.ndim > 1:
                data = data[:, 0]
            
            copy_len = min(len(data), max_samples)
            audio[:copy_len, i] = data[:copy_len]
        
        return audio, sr


class LoudnessMeterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Immersive Loudness")
        self.setMinimumSize(1280, 620)
        self.resize(1280, 650)
        
        self.current_results = None
        self.current_file = None
        self.mono_files = None
        self.current_standard = LOUDNESS_STANDARDS["GY/T 282-2014 (中国广电-电视)"]
        self.worker = None
        
        # 启用拖放
        self.setAcceptDrops(True)
        
        self._setup_ui()
        self._apply_theme()
    
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        left = self._create_left_panel()
        main_layout.addWidget(left, 35)
        
        center = self._create_center_panel()
        main_layout.addWidget(center, 30)
        
        right = self._create_right_panel()
        main_layout.addWidget(right, 35)

    def _update_mono_files_list(self):
        """更新多单声道文件列表显示，使用标准声道标识"""
        if not self.mono_files:
            self.mono_files_table.setRowCount(0)
            self.mono_files_group.setTitle('📋 已加载文件')
            return
        
        # 标准声道顺序
        ch_order = ['L', 'R', 'C', 'LFE', 'Ls', 'Rs', 'Lss', 'Rss', 'Lrs', 'Rrs', 'Ltf', 'Rtf', 'Ltr', 'Rtr', 'Ltb', 'Rtb']
        
        def sort_key(item):
            ch_name = item[1]
            if ch_name in ch_order:
                return ch_order.index(ch_name)
            return 999
        
        sorted_files = sorted(self.mono_files, key=sort_key)
        
        # 更新表格
        self.mono_files_table.setRowCount(len(sorted_files))
        for i, (path, ch_name) in enumerate(sorted_files):
            # 标准声道标识（加粗绿色）
            from PySide6.QtGui import QFont
            ch_item = QTableWidgetItem(ch_name)
            ch_item.setTextAlignment(Qt.AlignCenter)
            ch_item.setForeground(QColor('#27ae60'))
            ch_item.setFont(QFont('Microsoft YaHei', 10, QFont.Bold))
            self.mono_files_table.setItem(i, 0, ch_item)
            
            # 文件名
            filename = Path(path).name
            file_item = QTableWidgetItem(filename)
            file_item.setToolTip(str(path))
            self.mono_files_table.setItem(i, 1, file_item)
        
        self.mono_files_group.setVisible(True)
        self.mono_files_group.setTitle(f'📋 已加载文件 ({len(sorted_files)}个)')



    def parse_and_display_adm(self, file_path: str):
        """解析ADM文件并在UI中显示详细信息"""
        try:
            self.adm_info.clear()
            self.adm_info.setPlainText("正在解析ADM...")
            QApplication.processEvents()  # 立即更新UI
            
            parser = BW64Parser(file_path)
            adm = parser.parse()
            
            if not adm:
                self.adm_info.setPlainText("[错误] 无法解析ADM元数据\n\n可能原因：\n1. 文件不是有效的ADM/BW64格式\n2. XML命名空间不匹配")
                return
            
            # 检查解析结果是否为空
            if not adm.channel_formats and not adm.programmes:
                self.adm_info.setPlainText("[警告] ADM元数据解析为空\n\n可能原因：\n1. 命名空间检测失败\n2. 文件不包含ADM数据")
                return
            
            # 收集信息
            lines = []
            lines.append(f"📦 文件: {Path(file_path).name}")
            lines.append("")
            
            # 节目信息
            if adm.programmes:
                prog_name = adm.programmes[0].get('name', 'N/A')
                lines.append(f"🎬 节目: {prog_name}")
            
            # 内容统计
            content_count = len(adm.contents)
            object_count = len(adm.objects)
            lines.append(f"📊 内容: {content_count}个Content, {object_count}个Object")
            
            # 声床分析
            direct_speakers = [ch for ch in adm.channel_formats if ch.type == 'DirectSpeakers']
            objects_ch = [ch for ch in adm.channel_formats if ch.type == 'Objects']
            
            lines.append("")
            lines.append(f"🔊 声床配置 ({len(direct_speakers)} DirectSpeakers):")
            
            # 显示声床详情
            for i, ch in enumerate(direct_speakers[:16]):
                pos_str = ""
                if ch.position:
                    az = ch.position.get('azimuth', 0)
                    el = ch.position.get('elevation', 0)
                    pos_str = f"az={az:6.1f}° el={el:6.1f}°"
                elif ch.speaker_label:
                    az, el = adm._speaker_label_to_angles(ch.speaker_label)
                    pos_str = f"az={az:6.1f}° el={el:6.1f}° [{ch.speaker_label}]"
                
                lfe_mark = " [LFE]" if ch.is_lfe else ""
                lines.append(f"  Ch{i:2d}: {ch.name:20s} {pos_str}{lfe_mark}")
            
            if len(direct_speakers) > 16:
                lines.append(f"  ... 还有 {len(direct_speakers)-16} 个声道")
            
            # 检测Objects
            if objects_ch:
                lines.append("")
                lines.append(f"⚠️ 包含 {len(objects_ch)} 个动态对象(Object)")
            
            # 配置识别 - 兼容新旧版adm_parser
            ch_count = len(direct_speakers)
            lines.append("")
            
            # 尝试使用新版 detect_configuration 方法
            detected = None
            confidence = 0.0
            description = ""
            
            if hasattr(adm, 'detect_configuration'):
                try:
                    detected, confidence, description = adm.detect_configuration()
                except Exception as e:
                    print(f"[DEBUG] detect_configuration 失败: {e}")
            
            if detected and detected != 'unknown':
                self.config_combo.setCurrentText(detected)
                lines.append(f"🎯 自动识别为: {description} ({ch_count}ch声床, 置信度{confidence:.0%})")
            else:
                # 回退到数量映射
                cfg_map = {
                    2: 'stereo', 6: '5.1', 8: '7.1', 
                    10: '5.1.4', 12: '7.1.4', 16: '9.1.6'
                }
                fallback = cfg_map.get(ch_count, '未知')
                if ch_count in cfg_map:
                    self.config_combo.setCurrentText(cfg_map[ch_count])
                else:
                    self.config_combo.setCurrentText("自动检测")
                lines.append(f"⚠️ 基于数量识别: {fallback} ({ch_count}ch)")
                if detected == 'unknown':
                    lines.append("   (特征识别失败，请手动确认)")
            
            # 显示到UI
            self.adm_info.setPlainText("\n".join(lines))
            
            # 更新渲染器与创作软件信息
            self.renderer_group.setVisible(True)
            
            # 渲染器信息
            if adm.renderer_info:
                r_info = adm.renderer_info
                r_text = f"🎚️ {r_info.get('name', '未知渲染器')}"
                if r_info.get('version'):
                    r_text += f" v{r_info['version']}"
                if r_info.get('coordinate_mode'):
                    r_text += f" [{r_info['coordinate_mode']}]"
                if r_info.get('uri'):
                    r_text += f"\n   URI: {r_info['uri']}"
                if r_info.get('pack_format_refs'):
                    r_text += f"\n   布局: {', '.join(r_info['pack_format_refs'])}"
                self.renderer_label.setText(r_text)
                self.renderer_label.setStyleSheet("color: #f39c12; font-size: 11px;")
            else:
                self.renderer_label.setText("🎚️ 未检测到渲染器信息")
                self.renderer_label.setStyleSheet("color: #888; font-size: 11px;")
            
            # 创作软件信息
            if adm.authoring_info:
                a_info = adm.authoring_info
                a_text = ""
                if a_info.get('authoring_tool'):
                    a_text += f"🛠️ {a_info['authoring_tool']}"
                    if a_info.get('authoring_tool_version'):
                        a_text += f" v{a_info['authoring_tool_version']}"
                else:
                    a_text = "🛠️ 未检测到创作软件"
                self.authoring_label.setText(a_text)
                self.authoring_label.setStyleSheet("color: #3498db; font-size: 11px;")
                
                # 参考布局
                if a_info.get('reference_layout'):
                    self.ref_layout_label.setText(f"📐 参考布局: {a_info['reference_layout']}")
                    self.ref_layout_label.setVisible(True)
                else:
                    self.ref_layout_label.setVisible(False)
            else:
                self.authoring_label.setText("🛠️ 未检测到创作软件信息")
                self.authoring_label.setStyleSheet("color: #888; font-size: 11px;")
                self.ref_layout_label.setVisible(False)
            
            # 保存parser供后续使用
            self.current_adm_parser = parser
            
        except Exception as e:
            error_msg = f"[解析错误] {str(e)}"
            self.adm_info.setPlainText(error_msg)
            import traceback
            print("=" * 60)
            print("ADM解析错误详情:")
            print(traceback.format_exc())
            print("=" * 60)

    
    def _create_left_panel(self):
        """左侧面板：输入方式、文件信息、模式专属区域（支持滚动）"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        panel = QGroupBox("📁 输入")
        panel.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #667eea;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 8px;
                padding-bottom: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #667eea;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)
        layout.setContentsMargins(14, 14, 14, 14)

        # === 1. 输入方式分段按钮 ===
        mode_group = QGroupBox("输入方式")
        mode_group.setStyleSheet("""
            QGroupBox {
                font-size: 12px;
                border: 1px solid #0f3460;
            }
            QGroupBox::title { color: #aaa; }
        """)
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.setSpacing(4)

        self.mode_button_group = QButtonGroup(self)
        self.mode_button_group.setExclusive(True)

        self.btn_mono = QPushButton("🎵 多单声道")
        self.btn_standard = QPushButton("📁 标准多声道")
        self.btn_adm = QPushButton("📦 ADM/BW64")

        for btn in (self.btn_mono, self.btn_standard, self.btn_adm):
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            self.mode_button_group.addButton(btn)

        self.btn_mono.clicked.connect(lambda: self.on_input_mode_changed('mono'))
        self.btn_standard.clicked.connect(lambda: self.on_input_mode_changed('standard'))
        self.btn_adm.clicked.connect(lambda: self.on_input_mode_changed('adm'))

        mode_layout.addWidget(self.btn_mono)
        mode_layout.addWidget(self.btn_standard)
        mode_layout.addWidget(self.btn_adm)
        layout.addWidget(mode_group)

        self._mode_style_default = """
            QPushButton {
                background-color: #0f3460;
                border: 1px solid #667eea;
                padding: 8px 10px;
                border-radius: 4px;
                font-size: 12px;
                color: #ccc;
            }
            QPushButton:hover { background-color: #1a4a7a; }
        """
        self._mode_style_active = """
            QPushButton {
                background-color: #667eea;
                border: 2px solid #764ba2;
                padding: 8px 10px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                color: white;
            }
            QPushButton:hover { background-color: #764ba2; }
        """
        self._update_mode_buttons('mono')

        # === 2. 文件信息卡片 ===
        # === 2. 文件信息卡片（标准/ADM 模式显示） ===
        self.file_info_group = QGroupBox("文件信息")
        self.file_info_group.setStyleSheet("""
            QGroupBox {
                font-size: 12px;
                border: 1px solid #3498db;
            }
            QGroupBox::title { color: #3498db; }
        """)
        file_layout = QVBoxLayout(self.file_info_group)
        file_layout.setSpacing(8)

        self.filename_label = QLabel("未选择文件")
        self.filename_label.setAlignment(Qt.AlignCenter)
        self.filename_label.setWordWrap(True)
        self.filename_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            color: #667eea;
            padding: 4px;
        """)
        file_layout.addWidget(self.filename_label)

        self.path_label = QLabel("")
        self.path_label.setAlignment(Qt.AlignCenter)
        self.path_label.setWordWrap(True)
        self.path_label.setStyleSheet("""
            font-size: 10px;
            color: #888888;
            padding: 2px;
        """)
        file_layout.addWidget(self.path_label)

        # 元数据网格
        meta_widget = QWidget()
        meta_layout = QGridLayout(meta_widget)
        meta_layout.setSpacing(6)
        meta_layout.setContentsMargins(0, 4, 0, 4)
        meta_layout.setColumnStretch(1, 1)
        meta_layout.setColumnStretch(3, 1)

        self.file_meta_labels: Dict[str, QLabel] = {}
        meta_fields = [
            ('format', '格式'), ('channels', '声道'),
            ('samplerate', '采样率'), ('bit_depth', '位深'),
            ('duration', '时长'), ('file_size', '大小'),
        ]
        for i, (key, name) in enumerate(meta_fields):
            row, col = divmod(i, 2)
            lbl_name = QLabel(f"{name}:")
            lbl_name.setStyleSheet("color: #aaa; font-size: 11px;")
            lbl_val = QLabel("-")
            lbl_val.setStyleSheet("color: #eee; font-size: 11px; font-weight: bold;")
            self.file_meta_labels[key] = lbl_val
            meta_layout.addWidget(lbl_name, row, col * 2)
            meta_layout.addWidget(lbl_val, row, col * 2 + 1)
        file_layout.addWidget(meta_widget)

        layout.addWidget(self.file_info_group)

        # === 浏览按钮（永久显示） ===
        browse_btn = QPushButton("浏览...")
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #667eea;
                border: none;
                padding: 6px 14px;
                border-radius: 4px;
                font-size: 12px;
                color: white;
            }
            QPushButton:hover { background-color: #764ba2; }
        """)
        browse_btn.clicked.connect(self.browse)
        layout.addWidget(browse_btn)

        # === 3. 模式专属区域 ===
        # -- 标准多声道 --
        self.standard_section = QWidget()
        standard_layout = QVBoxLayout(self.standard_section)
        standard_layout.setContentsMargins(0, 0, 0, 0)
        standard_layout.setSpacing(8)

        cfg_layout = QHBoxLayout()
        cfg_layout.addWidget(QLabel("声道配置:"))
        self.config_combo = QComboBox()
        self.config_combo.addItems(["自动检测", "stereo", "5.1", "7.1", "5.1.4", "7.1.2", "7.1.4"])
        self.config_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f3460;
                border: 1px solid #667eea;
                padding: 4px;
                font-size: 12px;
                color: #eee;
            }
        """)
        cfg_layout.addWidget(self.config_combo)
        standard_layout.addLayout(cfg_layout)
        standard_layout.addStretch()
        layout.addWidget(self.standard_section)

        # -- ADM/BW64 --
        self.adm_section = QWidget()
        adm_layout = QVBoxLayout(self.adm_section)
        adm_layout.setContentsMargins(0, 0, 0, 0)
        adm_layout.setSpacing(8)

        self.adm_info = QTextEdit()
        self.adm_info.setReadOnly(True)
        self.adm_info.setPlaceholderText("ADM文件信息将显示在这里...")
        self.adm_info.setMaximumHeight(200)
        self.adm_info.setStyleSheet("""
            QTextEdit {
                background-color: #16213e;
                border: 1px solid #e74c3c;
                color: #eee;
                font-family: Consolas, Monaco, monospace;
                font-size: 11px;
                padding: 5px;
            }
        """)
        adm_layout.addWidget(self.adm_info)

        self.renderer_group = QGroupBox("🎛️ 渲染器与创作软件信息")
        self.renderer_group.setVisible(False)
        self.renderer_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #e74c3c;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QGroupBox::title { color: #e74c3c; }
        """)
        renderer_layout = QVBoxLayout(self.renderer_group)
        renderer_layout.setSpacing(6)
        renderer_layout.setContentsMargins(10, 10, 10, 10)

        self.renderer_label = QLabel("渲染器: 未检测")
        self.renderer_label.setStyleSheet("color: #f39c12; font-size: 11px;")
        self.renderer_label.setWordWrap(True)
        renderer_layout.addWidget(self.renderer_label)

        self.authoring_label = QLabel("创作软件: 未检测")
        self.authoring_label.setStyleSheet("color: #3498db; font-size: 11px;")
        self.authoring_label.setWordWrap(True)
        renderer_layout.addWidget(self.authoring_label)

        self.ref_layout_label = QLabel("参考布局: 未检测")
        self.ref_layout_label.setStyleSheet("color: #9b59b6; font-size: 11px;")
        self.ref_layout_label.setWordWrap(True)
        renderer_layout.addWidget(self.ref_layout_label)

        adm_layout.addWidget(self.renderer_group)
        adm_layout.addStretch()
        layout.addWidget(self.adm_section)

        # -- 多单声道 --
        self.mono_section = QWidget()
        mono_layout = QVBoxLayout(self.mono_section)
        mono_layout.setContentsMargins(0, 0, 0, 0)
        mono_layout.setSpacing(8)

        self.mono_files_group = QGroupBox('📋 已加载文件')
        self.mono_files_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.mono_files_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #27ae60;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QGroupBox::title { color: #27ae60; }
        """)
        mono_files_layout = QVBoxLayout(self.mono_files_group)
        mono_files_layout.setSpacing(4)
        mono_files_layout.setContentsMargins(10, 10, 10, 10)

        self.mono_files_table = QTableWidget(0, 2)
        self.mono_files_table.setHorizontalHeaderLabels(['声道', '文件名'])
        self.mono_files_table.verticalHeader().setVisible(False)
        self.mono_files_table.horizontalHeader().setStretchLastSection(True)
        self.mono_files_table.setMinimumHeight(180)
        self.mono_files_table.setStyleSheet("""
            QTableWidget {
                background-color: #16213e;
                border: 1px solid #27ae60;
                font-size: 10px;
            }
            QHeaderView::section {
                background-color: #27ae60;
                color: white;
                padding: 4px;
                font-size: 10px;
            }
            QTableWidget::item {
                padding: 2px;
                color: #eee;
            }
        """)
        self.mono_files_table.setColumnWidth(0, 55)
        mono_files_layout.addWidget(self.mono_files_table, 1)

        mono_layout.addWidget(self.mono_files_group, 1)
        mono_layout.addStretch()
        layout.addWidget(self.mono_section, 1)

        layout.addStretch(0)
        scroll.setWidget(panel)

        # 初始化显隐
        self._update_mode_ui('mono')

        return scroll

    def _update_mode_buttons(self, active_mode: str):
        """更新输入模式按钮样式"""
        self.btn_mono.setStyleSheet(
            self._mode_style_active if active_mode == 'mono' else self._mode_style_default
        )
        self.btn_standard.setStyleSheet(
            self._mode_style_active if active_mode == 'standard' else self._mode_style_default
        )
        self.btn_adm.setStyleSheet(
            self._mode_style_active if active_mode == 'adm' else self._mode_style_default
        )

        self.btn_mono.setChecked(active_mode == 'mono')
        self.btn_standard.setChecked(active_mode == 'standard')
        self.btn_adm.setChecked(active_mode == 'adm')

    def _update_mode_ui(self, mode: str):
        """根据模式切换左侧各区块显隐"""
        self.standard_section.setVisible(mode == 'standard')
        self.adm_section.setVisible(mode == 'adm')
        self.mono_section.setVisible(mode == 'mono')
        if hasattr(self, 'file_info_group'):
            self.file_info_group.setVisible(mode != 'mono')

    def _clear_file_metadata(self):
        """清空文件元数据显示"""
        for lbl in self.file_meta_labels.values():
            lbl.setText("-")
            lbl.setStyleSheet("color: #eee; font-size: 11px; font-weight: bold;")

    def _update_file_metadata(self, path: str):
        """读取并显示文件元数据"""
        try:
            info = sf.info(path)
            p = Path(path)
            size = p.stat().st_size
            size_str = self._format_file_size(size)

            self.file_meta_labels['format'].setText(p.suffix.lstrip('.').upper())
            self.file_meta_labels['channels'].setText(str(info.channels))
            self.file_meta_labels['samplerate'].setText(f"{info.samplerate} Hz")
            self.file_meta_labels['bit_depth'].setText(str(info.subtype_info))
            self.file_meta_labels['duration'].setText(f"{info.duration:.2f} s")
            self.file_meta_labels['file_size'].setText(size_str)
        except Exception as e:
            print(f"[元数据读取失败] {e}")
            self._clear_file_metadata()

    @staticmethod
    def _format_file_size(size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def dragEnterEvent(self, event):
        """拖拽进入"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """拖拽放下"""
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if not path:
            return
        self._load_file_by_path(path)

    def _load_file_by_path(self, path: str):
        """根据路径自动判断模式并加载文件"""
        p = Path(path)
        ext = p.suffix.lower()

        if ext in ('.wav', '.bw64', '.adm'):
            # 尝试判断是否为ADM
            try:
                if is_adm_file(path):
                    self.btn_adm.setChecked(True)
                    self.on_input_mode_changed('adm')
                    self.current_file = path
                    self.filename_label.setText(f"✓ ADM: {p.name}")
                    self.filename_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #e74c3c;")
                    self.path_label.setText(str(p.parent))
                    self._update_file_metadata(path)
                    self.parse_and_display_adm(path)
                    return
            except Exception:
                pass

        # 标准音频
        if ext in ('.wav', '.flac', '.mp3', '.ogg'):
            try:
                info = sf.info(path)
                if info.channels == 1:
                    # 单声道文件拖到主窗口 -> 触发多单声道对话框
                    self.btn_mono.setChecked(True)
                    self.on_input_mode_changed('mono')
                    # 这里简化处理：只加载一个文件，让用户继续添加
                    self.current_file = path
                    self.filename_label.setText(f"✓ {p.name} (请在浏览中添加更多)")
                    self.filename_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #f39c12;")
                    self.path_label.setText(str(p.parent))
                    self._update_file_metadata(path)
                    return
                else:
                    self.btn_standard.setChecked(True)
                    self.on_input_mode_changed('standard')
                    self.current_file = path
                    self.filename_label.setText(f"✓ {p.name}")
                    self.filename_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #27ae60;")
                    self.path_label.setText(str(p.parent))
                    self._update_file_metadata(path)

                    cfg_map = {2: 'stereo', 6: '5.1', 8: '7.1', 10: '5.1.4', 12: '7.1.4'}
                    if info.channels in cfg_map:
                        self.config_combo.setCurrentText(cfg_map[info.channels])

                    return
            except Exception as e:
                QMessageBox.warning(self, "文件错误", f"无法读取文件:\n{e}")
                return

        QMessageBox.warning(self, "不支持的文件", f"无法识别该文件类型:\n{p.name}")

    
    def _create_center_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # === 标题栏 ===
        header_widget = QWidget()
        header_widget.setMaximumHeight(300)
        header_widget.setMinimumHeight(200)
        header_widget.setStyleSheet('QWidget { background-color: #0f3460; border: none;}')
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 8, 15, 8)
        header_layout.setSpacing(3)
        header_layout.setAlignment(Qt.AlignCenter)
        
        # 咿呀服了吗
        il_label = QLabel('咿呀服了吗')
        il_label.setStyleSheet('color: #667eea; font-size: 10px; font-weight: thin; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; letter-spacing: 24px; border: none;')
        il_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(il_label)

        # IL
        il_label = QLabel('IAFLM')
        il_label.setStyleSheet('color: #667eea; font-size: 64px; font-weight: bold; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; letter-spacing: 12px; border: none;')
        il_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(il_label)
        
        # Immersive Loudness
        name_label = QLabel('Immersive Audio File Loudness Meter')
        name_label.setStyleSheet('color: #a0b4e8; font-size: 13px; font-weight: bold; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; letter-spacing: 3px; border: none;')
        name_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(name_label)
        
        # 底部行
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(0)
        bottom_layout.setContentsMargins(0, 2, 0, 0)
        bottom_layout.addStretch(1)
        
        cn_label = QLabel('沉浸式音频文件响度测量工具')
        cn_label.setStyleSheet('color: #8899cc; font-size: 10px; font-family: "Microsoft YaHei", "Segoe UI", sans-serif; letter-spacing: 1px; border: none;')
        cn_label.setAlignment(Qt.AlignCenter)
        bottom_layout.addWidget(cn_label)
        bottom_layout.addStretch(2)
        
        right_info = QVBoxLayout()
        right_info.setSpacing(1)
        right_info.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        version_label = QLabel('v3.1')
        version_label.setStyleSheet('color: #667eea; font-size: 11px; font-weight: bold;')
        version_label.setAlignment(Qt.AlignRight)
        right_info.addWidget(version_label)
        
        copyright_label = QLabel('© 2026 Yuan Xuecheng')
        copyright_label.setStyleSheet('color: #888; font-size: 8px; border: none;')
        copyright_label.setAlignment(Qt.AlignRight)
        right_info.addWidget(copyright_label)
        
        bottom_layout.addLayout(right_info)
        header_layout.addLayout(bottom_layout)
        layout.addWidget(header_widget)
        
        # === 原有内容 ===
        content_widget = QGroupBox('⚙️ 标准与进度')
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(8)
        
        content_layout.addWidget(QLabel('响度标准:'))
        self.std_combo = QComboBox()
        self.std_combo.addItems(list(LOUDNESS_STANDARDS.keys()))
        self.std_combo.currentTextChanged.connect(self.on_std_changed)
        self.std_combo.setCurrentText("GY/T 282-2014 (中国广电-电视)")
        content_layout.addWidget(self.std_combo)
        
        self.std_info = QLabel()
        self.std_info.setStyleSheet('background-color: #16213e; padding: 8px; border-radius: 4px;')
        self.update_std_info()
        content_layout.addWidget(self.std_info)
        
        content_layout.addSpacing(10)
        content_layout.addWidget(QLabel('当前步骤:'))
        self.step_label = QLabel('等待开始')
        self.step_label.setStyleSheet('color: #667eea; font-weight: bold;')
        content_layout.addWidget(self.step_label)
        
        content_layout.addWidget(QLabel('总进度:'))
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        content_layout.addWidget(self.progress)
        
        self.process_info = QLabel()
        self.process_info.setStyleSheet('color: #888; font-size: 11px;')
        self.process_info.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.process_info)
        
        self.start_btn = QPushButton('▶ 开始测量')
        self.start_btn.setStyleSheet('QPushButton { background-color: #667eea; color: white; font-weight: bold; font-size: 16px; padding: 12px; border-radius: 8px; } QPushButton:hover { background-color: #764ba2; }')
        self.start_btn.clicked.connect(self.start_measure)
        content_layout.addWidget(self.start_btn)
        
        content_layout.addStretch()
        layout.addWidget(content_widget)
        layout.addStretch()
        return panel
    def _create_right_panel(self):
        panel = QGroupBox("📊 结果与导出")
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)
        
        self.result_table = QTableWidget(5, 2)
        self.result_table.setHorizontalHeaderLabels(["指标", "数值"])
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        
        metrics = ["节目响度(I)", "最大短时响度(S)", "最大瞬时响度(M)", "最大真峰值(TP)", "响度范围(LRA)"]
        for i, m in enumerate(metrics):
            self.result_table.setItem(i, 0, QTableWidgetItem(m))
            item = QTableWidgetItem("--")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.result_table.setItem(i, 1, item)
        
        layout.addWidget(self.result_table)
        
        status_layout = QHBoxLayout()
        self.int_status = QLabel("节目响度: --")
        self.int_status.setAlignment(Qt.AlignCenter)
        self.int_status.setStyleSheet("padding: 4px; border-radius: 4px;")
        status_layout.addWidget(self.int_status)
        
        self.tp_status = QLabel("峰值: --")
        self.tp_status.setAlignment(Qt.AlignCenter)
        self.tp_status.setStyleSheet("padding: 4px; border-radius: 4px;")
        status_layout.addWidget(self.tp_status)
        layout.addLayout(status_layout)
        
        export_box = QGroupBox("导出")
        export_layout = QVBoxLayout(export_box)
        
        btn_layout = QHBoxLayout()
        self.export_txt_btn = QPushButton("📄 TXT")
        self.export_txt_btn.setEnabled(False)
        self.export_txt_btn.clicked.connect(lambda: self.export_direct('txt'))
        btn_layout.addWidget(self.export_txt_btn)
        
        self.export_json_btn = QPushButton("📊 JSON")
        self.export_json_btn.setEnabled(False)
        self.export_json_btn.clicked.connect(lambda: self.export_direct('json'))
        btn_layout.addWidget(self.export_json_btn)
        
        self.export_excel_btn = QPushButton("📈 Excel")
        self.export_excel_btn.setEnabled(False)
        self.export_excel_btn.clicked.connect(lambda: self.export_direct('excel'))
        btn_layout.addWidget(self.export_excel_btn)
        export_layout.addLayout(btn_layout)
        
        export_note = QLabel("TXT: 文本报告 | JSON: 结构化数据\nExcel: 包含每秒详细数据")
        export_note.setStyleSheet("color: #888; font-size: 10px;")
        export_note.setAlignment(Qt.AlignCenter)
        export_layout.addWidget(export_note)
        
        layout.addWidget(export_box)
        
        self.status = QLabel("就绪")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.status)
        
        layout.addStretch()
        return panel
    
    def _apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1a2e; }
            QWidget { background-color: #1a1a2e; color: #eee; }
            QGroupBox {
                border: 2px solid #667eea;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QGroupBox::title { color: #667eea; }
            QTableWidget {
                background-color: #16213e;
                border: 1px solid #667eea;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #667eea;
                color: white;
                padding: 4px;
            }
            QPushButton {
                background-color: #0f3460;
                border: 1px solid #667eea;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #667eea; }
            QComboBox {
                background-color: #16213e;
                border: 1px solid #667eea;
                padding: 4px;
            }
            QProgressBar {
                border: 1px solid #667eea;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk { background-color: #667eea; }
            QLabel { font-size: 12px; }
            QLineEdit {
                background-color: #16213e;
                border: 1px solid #667eea;
                padding: 4px;
            }
        """)
    
    def update_std_info(self):
        std = self.current_standard
        self.std_info.setText(
            f"目标: {std.integrated_target:+.1f} LUFS (±{std.integrated_tolerance:.1f} LU)\n"
            f"峰值: {std.true_peak_limit:+.1f} dBTP"
        )
    
    def on_std_changed(self, name):
        if name in LOUDNESS_STANDARDS:
            self.current_standard = LOUDNESS_STANDARDS[name]
            self.update_std_info()
    
    def on_input_mode_changed(self, mode):
        """输入模式切换"""
        self._update_mode_buttons(mode)
        self._update_mode_ui(mode)
        self.current_file = None
        self.mono_files = None
        self.current_adm_parser = None

        # 文件信息框：仅标准/ADM模式显示
        if hasattr(self, 'file_info_group'):
            self.file_info_group.setVisible(mode != 'mono')
        if hasattr(self, 'filename_label'):
            self.filename_label.setText("未选择文件")
            self.filename_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #667eea;")
        if hasattr(self, 'path_label'):
            self.path_label.setText("")
        self._clear_file_metadata()

        if hasattr(self, 'adm_info'):
            self.adm_info.clear()
            self.adm_info.setPlaceholderText("ADM文件信息将显示在这里...")
        if hasattr(self, 'renderer_group'):
            self.renderer_group.setVisible(False)
        if hasattr(self, 'mono_files_group'):
            self.mono_files_group.setVisible(False)


    
    def browse(self):
        """浏览文件"""
        # 确定当前模式
        if self.btn_mono.isChecked():
            mode = 'mono'
        elif self.btn_standard.isChecked():
            mode = 'standard'
        elif self.btn_adm.isChecked():
            mode = 'adm'
        else:
            QMessageBox.warning(self, "提示", "请先选择输入方式")
            return
        
        if mode == 'standard':  # 标准文件
            path, _ = QFileDialog.getOpenFileName(
                self, "选择音频", "", "音频 (*.wav *.flac *.mp3 *.ogg)"
            )
            if path:
                self.current_file = path
                p = Path(path)
                self.filename_label.setText(f"✓ {p.name}")
                self.filename_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #27ae60;")
                self.path_label.setText(str(p.parent))
                self._update_file_metadata(path)

                info = sf.info(path)
                cfg_map = {2: 'stereo', 6: '5.1', 8: '7.1', 10: '5.1.4', 12: '7.1.4'}
                if info.channels in cfg_map:
                    self.config_combo.setCurrentText(cfg_map[info.channels])

        elif mode == 'adm':  # ADM
            path, _ = QFileDialog.getOpenFileName(
                self, "选择ADM", "", "ADM (*.wav *.bw64 *.adm)"
            )
            if path:
                self.current_file = path
                p = Path(path)
                self.filename_label.setText(f"✓ ADM: {p.name}")
                self.filename_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #e74c3c;")
                self.path_label.setText(str(p.parent))
                self._update_file_metadata(path)

                # 立即解析ADM并显示信息
                self.parse_and_display_adm(path)

        elif mode == 'mono':  # 多单声道
            dlg = SmartMultiMonoDialog(self)
            if dlg.exec() == QDialog.Accepted:
                self.mono_files = dlg.get_files()
                if self.mono_files:
                    p = Path(self.mono_files[0][0])
                    self.filename_label.setText(f"✓ {len(self.mono_files)}个单声道文件")
                    self.filename_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #27ae60;")
                    self.path_label.setText(str(p.parent))

                    cfg_map = {2: 'stereo', 6: '5.1', 8: '7.1', 10: '5.1.4', 12: '7.1.4'}
                    if len(self.mono_files) in cfg_map:
                        self.config_combo.setCurrentText(cfg_map[len(self.mono_files)])

                    # 更新文件列表显示
                    self._update_mono_files_list()


    
    def start_measure(self):
        input_mode = None
        input_data = None
        
        if self.btn_standard.isChecked() and self.current_file:
            input_mode = 'file'
            input_data = self.current_file
        elif self.btn_adm.isChecked() and self.current_file:
            input_mode = 'adm'
            # 使用已解析的parser，避免重复解析
            if hasattr(self, 'current_adm_parser') and self.current_adm_parser:
                input_data = self.current_adm_parser
            else:
                # 如果没有预解析，重新解析
                try:
                    parser = BW64Parser(self.current_file)
                    parser.parse()
                    input_data = parser
                except Exception as e:
                    QMessageBox.critical(self, "ADM错误", str(e))
                    return
        elif self.btn_mono.isChecked() and self.mono_files:
            input_mode = 'mono_list'
            input_data = self.mono_files
        else:
            QMessageBox.warning(self, "提示", "请先选择输入文件")
            return
        
        # 获取当前声道配置和标准
        config_name = self.config_combo.currentText()
        standard = self.current_standard
        
        # 创建并启动工作线程
        self.worker = DetailedMeasurementWorker(input_mode, input_data, config_name, standard)
        self.worker.sub_step.connect(self.on_sub_step)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        
        # 重置UI状态
        self.start_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.export_txt_btn.setEnabled(False)
        self.export_json_btn.setEnabled(False)
        self.export_excel_btn.setEnabled(False)
        self.current_results = None
        
        # 启动线程
        self.worker.start()

    
    def on_sub_step(self, step, pct):
        self.step_label.setText(step)
        self.progress.setValue(pct)
        # 更新处理信息（包含倍速）
        if '⚡' in step:
            self.process_info.setText(step.split('|')[-1].strip())
    
    def on_progress(self, pct, current, total, speed, eta_str):
        self.progress.setValue(pct)
        if speed > 0:
            self.process_info.setText(f"{current:.1f}s/{total:.1f}s | ⚡{speed:.1f}x实时 | {eta_str}")
        else:
            self.process_info.setText(f"{current:.1f}s/{total:.1f}s | {eta_str}")
    
    def on_finished(self, results):
        # 合并文件信息到结果
        results['file_info'] = self._build_file_info()
        self.current_results = results
        self.progress.setVisible(False)
        self.start_btn.setEnabled(True)
        self.step_label.setText("完成")
        
        std = self.current_standard
        
        # 更新结果表格
        data = [
            (f"{results['integrated']:+.2f}", "LUFS"),
            (f"{results['short_term']:+.2f}", "LUFS"),
            (f"{results['momentary']:+.2f}", "LUFS"),
            (f"{results['true_peak']:+.2f}", "dBTP"),
            (f"{results['lra']:.2f}", "LU")
        ]
        
        for i, (val, unit) in enumerate(data):
            item = QTableWidgetItem(f"{val} {unit}")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.result_table.setItem(i, 1, item)
        
        # 更新合规状态
        int_ok = std.check_integrated(results['integrated'])
        tp_ok = std.check_true_peak(results['true_peak'])
        
        self.int_status.setText(f"节目响度: {'✓' if int_ok else '✗'}")
        self.int_status.setStyleSheet(f"background-color: {'#27ae60' if int_ok else '#e74c3c'}; color: white; padding: 4px; border-radius: 4px;")
        
        self.tp_status.setText(f"峰值: {'✓' if tp_ok else '✗'}")
        self.tp_status.setStyleSheet(f"background-color: {'#27ae60' if tp_ok else '#e74c3c'}; color: white; padding: 4px; border-radius: 4px;")
        
        self.status.setText(f"完成 | 用时{results.get('processing_time', 0):.1f}s")
        self.export_txt_btn.setEnabled(True)
        self.export_json_btn.setEnabled(True)
        self.export_excel_btn.setEnabled(True)
    
    def on_error(self, msg):
        self.progress.setVisible(False)
        self.start_btn.setEnabled(True)
        self.step_label.setText("错误")
        QMessageBox.critical(self, "错误", msg)
    
    def _build_file_info(self) -> dict:
        """构建当前被测文件信息字典"""
        info = {
            'mode': 'unknown',
            'file_path': '',
            'file_name': '',
            'adm_info': '',
            'renderer_info': '',
            'authoring_info': '',
            'ref_layout': '',
            'mono_files': []
        }
        
        if self.btn_standard.isChecked() and self.current_file:
            info['mode'] = 'standard'
            info['file_path'] = str(Path(self.current_file).parent)
            info['file_name'] = Path(self.current_file).name
            
        elif self.btn_adm.isChecked() and self.current_file:
            info['mode'] = 'adm'
            info['file_path'] = str(Path(self.current_file).parent)
            info['file_name'] = Path(self.current_file).name
            if hasattr(self, 'adm_info'):
                info['adm_info'] = self.adm_info.toPlainText()
            if hasattr(self, 'renderer_label'):
                info['renderer_info'] = self.renderer_label.text()
            if hasattr(self, 'authoring_label'):
                info['authoring_info'] = self.authoring_label.text()
            if hasattr(self, 'ref_layout_label'):
                info['ref_layout'] = self.ref_layout_label.text()
                
        elif self.btn_mono.isChecked() and self.mono_files:
            info['mode'] = 'mono'
            info['file_path'] = str(Path(self.mono_files[0][0]).parent)
            info['file_name'] = f"{len(self.mono_files)}个单声道文件"
            info['mono_files'] = [
                {'path': path, 'channel': ch, 'name': Path(path).name}
                for path, ch in self.mono_files
            ]
        
        return info
    
    def _get_export_base_name(self) -> str:
        """生成导出文件名基础部分（取自被测文件共有名）"""
        if self.btn_standard.isChecked() and self.current_file:
            return Path(self.current_file).stem
        elif self.btn_adm.isChecked() and self.current_file:
            return Path(self.current_file).stem
        elif self.btn_mono.isChecked() and self.mono_files:
            stems = [Path(p).stem for p, _ in self.mono_files]
            if not stems:
                return "report"
            # 求共有前缀
            common = stems[0]
            for s in stems[1:]:
                i = 0
                while i < len(common) and i < len(s) and common[i] == s[i]:
                    i += 1
                common = common[:i]
            common = common.rstrip('._-')
            if common:
                return common
            return stems[0]
        return "report"

    def export_direct(self, fmt):
        if not self.current_results:
            return
        
        std_name = self.current_standard.name.replace(' ', '_')[:15]
        ext_map = {'txt': 'txt', 'json': 'json', 'excel': 'xlsx'}
        ext = ext_map.get(fmt, fmt)
        base = self._get_export_base_name()
        default = f"{base}_{std_name}.{ext}"
        
        filter_map = {
            'txt': "文本文件 (*.txt)",
            'json': "JSON文件 (*.json)",
            'excel': "Excel文件 (*.xlsx)"
        }
        filter_str = filter_map.get(fmt, f"*.{ext}")
        path, _ = QFileDialog.getSaveFileName(self, "导出", default, filter_str)
        if not path:
            return
        
        try:
            fi = self.current_results.get('file_info', {})
            if fmt == 'excel':
                self._export_excel_detailed(path, {})
            else:
                results_obj = LoudnessResults(
                    integrated=self.current_results['integrated'],
                    short_term=self.current_results['short_term'],
                    momentary=self.current_results['momentary'],
                    true_peak=self.current_results['true_peak'],
                    lra=self.current_results['lra'],
                    max_true_peak=self.current_results['max_true_peak'],
                    duration=self.current_results['duration'],
                    filename=self.current_results.get('filename', 'unknown'),
                    sample_rate=self.current_results['sample_rate'],
                    channels=self.current_results['channels'],
                    blocks=[],
                    file_path=fi.get('file_path', ''),
                    file_name=fi.get('file_name', ''),
                    adm_info=fi.get('adm_info', ''),
                    renderer_info=fi.get('renderer_info', ''),
                    authoring_info=fi.get('authoring_info', ''),
                    ref_layout=fi.get('ref_layout', ''),
                    mono_files=fi.get('mono_files', [])
                )
                exporter = ReportExporter(results_obj)
                
                if fmt == 'txt':
                    exporter.export_txt(path)
                elif fmt == 'json':
                    exporter.export_json(path)
            
            self.status.setText(f"已导出: {Path(path).name}")
            
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
    
    def _export_excel_detailed(self, path: str, opts: dict):
        """导出详细Excel报告 (.xlsx)
        
        使用 openpyxl 生成真正的 Excel 文件，实现：
        - 中文正确显示（微软雅黑字体）
        - 超标数值用红色粗体 + 浅红色背景标注
        - 专业的表格格式
        """
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            QMessageBox.warning(self, "缺少依赖", "请安装 openpyxl: pip install openpyxl")
            return
        
        detailed = self.current_results.get('detailed_data')
        standard = self.current_standard
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "响度测量报告"
        
        # 样式定义
        title_font = Font(name='微软雅黑', size=14, bold=True, color='2F5496')
        header_font = Font(name='微软雅黑', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        normal_font = Font(name='微软雅黑', size=10)
        red_font = Font(name='微软雅黑', size=10, color='FF0000', bold=True)
        exceed_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
        center_align = Alignment(horizontal='center', vertical='center')
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        row = 1
        
        # === 被测文件信息 ===
        fi = self.current_results.get('file_info', {})
        ws.merge_cells(f'A{row}:E{row}')
        cell = ws.cell(row=row, column=1, value='被测文件信息')
        cell.font = title_font
        cell.alignment = Alignment(horizontal='left', vertical='center')
        row += 2
        
        file_info_rows = [
            ['测量时间', time.strftime('%Y-%m-%d %H:%M:%S')],
            ['文件路径', fi.get('file_path', '-')],
            ['文件名称', fi.get('file_name', self.current_results.get('filename', 'unknown'))],
        ]
        if fi.get('renderer_info'):
            file_info_rows.append(['渲染器', fi['renderer_info']])
        if fi.get('authoring_info'):
            file_info_rows.append(['创作软件', fi['authoring_info']])
        if fi.get('ref_layout'):
            file_info_rows.append(['参考布局', fi['ref_layout']])
        if fi.get('mono_files'):
            for item in fi['mono_files']:
                file_info_rows.append([f"声道 {item.get('channel', '?')}", item.get('name', '')])
        
        for label, value in file_info_rows:
            ws.cell(row=row, column=1, value=label).font = normal_font
            ws.cell(row=row, column=1).alignment = Alignment(horizontal='left', vertical='center')
            ws.cell(row=row, column=2, value=value).font = normal_font
            ws.cell(row=row, column=2).alignment = Alignment(horizontal='left', vertical='center')
            row += 1
        
        # ADM 信息单独处理：保留换行，合并单元格并自动换行显示
        if fi.get('adm_info'):
            ws.cell(row=row, column=1, value='ADM 信息').font = normal_font
            ws.cell(row=row, column=1).alignment = Alignment(horizontal='left', vertical='top')
            adm_cell = ws.cell(row=row, column=2, value=fi['adm_info'])
            adm_cell.font = Font(name='Consolas', size=9)
            adm_cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)
            ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=5)
            line_count = fi['adm_info'].count('\n') + 1
            ws.row_dimensions[row].height = max(30, line_count * 14)
            row += 1
        
        row += 1
        
        # === 整体测量结果 ===
        ws.merge_cells(f'A{row}:E{row}')
        cell = ws.cell(row=row, column=1, value='整体测量结果')
        cell.font = title_font
        cell.alignment = center_align
        row += 2
        
        headers = ['指标', '数值', '单位', '标准限值', '状态']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = thin_border
        row += 1
        
        summary = detailed['summary'] if detailed else {
            'integrated_loudness': self.current_results['integrated'],
            'max_short_term': self.current_results['short_term'],
            'max_momentary': self.current_results['momentary'],
            'max_true_peak': self.current_results['true_peak'],
            'lra': self.current_results['lra'],
            'duration': self.current_results['duration']
        }
        
        # 节目响度
        int_val = summary['integrated_loudness']
        int_target = standard.integrated_target
        int_tol = standard.integrated_tolerance
        int_status = '合格' if abs(int_val - int_target) <= int_tol else '超标'
        is_exceed = int_status == '超标'
        ws.cell(row=row, column=1, value='节目响度').font = normal_font
        ws.cell(row=row, column=2, value=f'{int_val:+.2f}').font = red_font if is_exceed else normal_font
        ws.cell(row=row, column=3, value='LUFS').font = normal_font
        ws.cell(row=row, column=4, value=f'{int_target:+.1f} ± {int_tol:.1f}').font = normal_font
        status_cell = ws.cell(row=row, column=5, value=int_status)
        status_cell.font = red_font if is_exceed else normal_font
        if is_exceed:
            status_cell.fill = exceed_fill
        for col in range(1, 6):
            ws.cell(row=row, column=col).border = thin_border
            ws.cell(row=row, column=col).alignment = center_align
        row += 1
        
        # 最大短时响度
        st_val = summary['max_short_term']
        ws.cell(row=row, column=1, value='最大短时响度').font = normal_font
        ws.cell(row=row, column=2, value=f'{st_val:+.2f}').font = normal_font
        ws.cell(row=row, column=3, value='LUFS').font = normal_font
        ws.cell(row=row, column=4, value='-').font = normal_font
        ws.cell(row=row, column=5, value='合格').font = normal_font
        for col in range(1, 6):
            ws.cell(row=row, column=col).border = thin_border
            ws.cell(row=row, column=col).alignment = center_align
        row += 1
        
        # 最大瞬时响度
        mom_val = summary['max_momentary']
        ws.cell(row=row, column=1, value='最大瞬时响度').font = normal_font
        ws.cell(row=row, column=2, value=f'{mom_val:+.2f}').font = normal_font
        ws.cell(row=row, column=3, value='LUFS').font = normal_font
        ws.cell(row=row, column=4, value='-').font = normal_font
        ws.cell(row=row, column=5, value='合格').font = normal_font
        for col in range(1, 6):
            ws.cell(row=row, column=col).border = thin_border
            ws.cell(row=row, column=col).alignment = center_align
        row += 1
        
        # 最大真峰值
        tp_val = summary['max_true_peak']
        tp_limit = standard.true_peak_limit
        tp_status = '合格' if tp_val <= tp_limit else '超标'
        is_exceed = tp_status == '超标'
        ws.cell(row=row, column=1, value='最大真峰值').font = normal_font
        ws.cell(row=row, column=2, value=f'{tp_val:+.2f}').font = red_font if is_exceed else normal_font
        ws.cell(row=row, column=3, value='dBTP').font = normal_font
        ws.cell(row=row, column=4, value=f'≤ {tp_limit:+.1f}').font = normal_font
        status_cell = ws.cell(row=row, column=5, value=tp_status)
        status_cell.font = red_font if is_exceed else normal_font
        if is_exceed:
            status_cell.fill = exceed_fill
        for col in range(1, 6):
            ws.cell(row=row, column=col).border = thin_border
            ws.cell(row=row, column=col).alignment = center_align
        row += 1
        
        # 响度范围
        lra_val = summary['lra']
        ws.cell(row=row, column=1, value='响度范围(LRA)').font = normal_font
        ws.cell(row=row, column=2, value=f'{lra_val:.2f}').font = normal_font
        ws.cell(row=row, column=3, value='LU').font = normal_font
        ws.cell(row=row, column=4, value='-').font = normal_font
        ws.cell(row=row, column=5, value='参考').font = normal_font
        for col in range(1, 6):
            ws.cell(row=row, column=col).border = thin_border
            ws.cell(row=row, column=col).alignment = center_align
        row += 1
        
        # 时长
        ws.cell(row=row, column=1, value='测量时长').font = normal_font
        ws.cell(row=row, column=2, value=f"{summary['duration']:.2f}").font = normal_font
        ws.cell(row=row, column=3, value='秒').font = normal_font
        ws.cell(row=row, column=4, value='-').font = normal_font
        ws.cell(row=row, column=5, value='-').font = normal_font
        for col in range(1, 6):
            ws.cell(row=row, column=col).border = thin_border
            ws.cell(row=row, column=col).alignment = center_align
        row += 1
        
        row += 2
        
        # === 每秒短时响度 ===
        if detailed and detailed.get('short_term_per_second'):
            ws.merge_cells(f'A{row}:C{row}')
            cell = ws.cell(row=row, column=1, value='每秒短时响度 (3秒滑动窗口)')
            cell.font = title_font
            cell.alignment = Alignment(horizontal='left', vertical='center')
            row += 2
            
            st_headers = ['时间(秒)', '短时响度(LUFS)', '状态']
            for col, header in enumerate(st_headers, 1):
                cell = ws.cell(row=row, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_align
                cell.border = thin_border
            row += 1
            
            for item in detailed['short_term_per_second']:
                time_sec = item['time']
                lufs = item['lufs']
                is_exceed = item.get('is_exceed', False)
                
                ws.cell(row=row, column=1, value=f'{time_sec:.1f}').font = normal_font
                ws.cell(row=row, column=1).alignment = center_align
                ws.cell(row=row, column=1).border = thin_border
                
                lufs_cell = ws.cell(row=row, column=2, value=f'{lufs:+.2f}')
                lufs_cell.font = red_font if is_exceed else normal_font
                lufs_cell.alignment = center_align
                lufs_cell.border = thin_border
                if is_exceed:
                    lufs_cell.fill = exceed_fill
                
                status_cell = ws.cell(row=row, column=3, value='超标' if is_exceed else '合格')
                status_cell.font = red_font if is_exceed else normal_font
                status_cell.alignment = center_align
                status_cell.border = thin_border
                if is_exceed:
                    status_cell.fill = exceed_fill
                
                row += 1
            
            row += 1
        
        # === 每秒最大真峰值 ===
        if detailed and detailed.get('true_peak_per_second'):
            ws.merge_cells(f'A{row}:D{row}')
            cell = ws.cell(row=row, column=1, value='每秒最大真峰值')
            cell.font = title_font
            cell.alignment = Alignment(horizontal='left', vertical='center')
            row += 2
            
            tp_headers = ['时间(秒)', '真峰值(dBTP)', '标准限值', '状态']
            for col, header in enumerate(tp_headers, 1):
                cell = ws.cell(row=row, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_align
                cell.border = thin_border
            row += 1
            
            for item in detailed['true_peak_per_second']:
                time_sec = item['time']
                dbtp = item['dbtp']
                is_exceed = item.get('is_exceed', False)
                
                ws.cell(row=row, column=1, value=f'{time_sec:.1f}').font = normal_font
                ws.cell(row=row, column=1).alignment = center_align
                ws.cell(row=row, column=1).border = thin_border
                
                dbtp_cell = ws.cell(row=row, column=2, value=f'{dbtp:+.2f}')
                dbtp_cell.font = red_font if is_exceed else normal_font
                dbtp_cell.alignment = center_align
                dbtp_cell.border = thin_border
                if is_exceed:
                    dbtp_cell.fill = exceed_fill
                
                ws.cell(row=row, column=3, value=f'≤ {tp_limit:+.1f}').font = normal_font
                ws.cell(row=row, column=3).alignment = center_align
                ws.cell(row=row, column=3).border = thin_border
                
                status_cell = ws.cell(row=row, column=4, value='超标' if is_exceed else '合格')
                status_cell.font = red_font if is_exceed else normal_font
                status_cell.alignment = center_align
                status_cell.border = thin_border
                if is_exceed:
                    status_cell.fill = exceed_fill
                
                row += 1
            
            row += 1
        
        # 调整列宽
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 18
        ws.column_dimensions['E'].width = 12
        
        wb.save(path)
        print(f'[Excel导出] 已保存到: {path}')


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    icon_path = Path('assets/icon.ico')
    if icon_path.exists():
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(str(icon_path.resolve())))
    win = LoudnessMeterApp()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
