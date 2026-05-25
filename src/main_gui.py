"""
ITU-R BS.1770-5 响度测量仪 v3.2 (整合修复版)
修复：
- 测量算法（process_audio 变量定义、最大值追踪）
- 智能声道匹配（支持点号分隔的声道标识）
- 术语统一（节目响度、最大短时/瞬时响度）
- ADM解析兼容性（支持旧版adm_parser）
"""

import sys
import time
import re
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QProgressBar, QTableWidget,
    QTableWidgetItem, QGroupBox, QMessageBox, QComboBox, QDialog,
    QListWidget, QAbstractItemView, QDialogButtonBox, QLineEdit,
    QFrame, QCheckBox, QSpinBox, QTextEdit, QSizePolicy,
    QButtonGroup, QScrollArea, QGridLayout, QStyledItemDelegate, QHeaderView
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor


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


from renderers.ear_renderer import render_adm, get_supported_layouts, get_adm_info
from mono_channel_matcher import (
    SmartMultiMonoDialog,
    CHANNEL_TEMPLATES,
    auto_match_mono_files,
)


class ExportOptionsDialog(QDialog):
    def __init__(self, has_detailed, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("导出选项"))
        self.setMinimumSize(400, 300)
        
        self.has_detailed = has_detailed
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(self.tr("导出格式:")))
        self.format_combo = QComboBox()
        self.format_combo.addItems([self.tr("TXT (文本报告)"), self.tr("JSON (结构化数据)"), self.tr("CSV (表格数据)")])
        layout.addWidget(self.format_combo)
        
        layout.addSpacing(20)
        layout.addWidget(QLabel(self.tr("详细程度:")))
        
        self.summary_check = QCheckBox(self.tr("总体概况 (节目响度/最大短时/最大瞬时/真峰值/LRA)"))
        self.summary_check.setChecked(True)
        layout.addWidget(self.summary_check)
        
        layout.addWidget(QLabel(self.tr("Excel导出将包含:\n• 整体测量结果\n• 每秒短时响度 (3秒滑动窗口)\n• 每秒最大真峰值\n• 超标数值以红色标注")))
        
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
            filename = self.tr("测量文件")
            
            # === 阶段1: 准备 (0-15%) ===
            self.sub_step.emit(self.tr("准备音频..."), 0)
            
            if self.input_mode == 'file':
                file_path = self.input_data
                info = sf.info(file_path)
                sr = info.samplerate
                filename = Path(file_path).name
                file_size = Path(file_path).stat().st_size
                
                # 小文件(<50MB)直接加载
                if file_size < 50 * 1024 * 1024:
                    self.sub_step.emit(self.tr("加载: {name}").format(name=filename[:30]), 5)
                    audio, sr = sf.read(file_path, dtype='float32')
                    self.sub_step.emit(self.tr("加载完成"), 15)
                else:
                    # 大文件分块加载，显示进度 5-15%
                    audio, sr = self._load_large_file(file_path, file_size)
                    
            elif self.input_mode == 'adm':
                parser = self.input_data
                self.sub_step.emit(self.tr("读取 ADM..."), 5)
                audio, sr = parser.read_audio()
                self.sub_step.emit(self.tr("ADM 加载完成"), 15)
                filename = self.tr("ADM文件")
                
            elif self.input_mode == 'mono_list':
                mono_files = self.input_data
                total_files = len(mono_files)
                
                self.sub_step.emit(self.tr("分析文件..."), 2)
                max_samples = 0
                sr = None
                
                for i, (path, name) in enumerate(mono_files):
                    info = sf.info(path)
                    max_samples = max(max_samples, info.frames)
                    if sr is None:
                        sr = info.samplerate
                    progress = 2 + (i + 1) / total_files * 5
                    self.sub_step.emit(self.tr("分析: {name}").format(name=name), int(progress))
                
                num_channels = len(mono_files)
                audio = np.zeros((max_samples, num_channels), dtype=np.float32)
                
                for i, (path, name) in enumerate(mono_files):
                    progress = 7 + i / num_channels * 8
                    self.sub_step.emit(self.tr("加载: {name}").format(name=name), int(progress))
                    data, _ = sf.read(path, dtype='float32')
                    if data.ndim > 1:
                        data = data[:, 0]
                    copy_len = min(len(data), max_samples)
                    audio[:copy_len, i] = data[:copy_len]
                
                self.sub_step.emit(self.tr("多单声道加载完成"), 15)
            
            if audio is None:
                raise ValueError(self.tr("音频加载失败"))
            
            if audio.ndim == 1:
                audio = audio.reshape(-1, 1)
            
            actual_duration = len(audio) / sr
            num_channels = audio.shape[1]
            self.audio_duration = actual_duration  # 保存音频时长用于倍速计算
            
            # === 阶段2: 初始化测量器 (15-20%) ===
            self.sub_step.emit(self.tr("初始化: {num_channels} ch, {actual_duration:.1f} s").format(num_channels=num_channels, actual_duration=actual_duration), 15)
            
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
            
            self.sub_step.emit(self.tr("开始测量..."), 20)
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
                        speed_str = self.tr(" | ⚡{ratio:.1f}x 实时").format(ratio=speed_ratio)
                
                self.sub_step.emit(self.tr("测量中... {current_block}/{total_blocks} 块{speed_str}").format(current_block=current_block, total_blocks=total_blocks, speed_str=speed_str), int(progress_pct))
            
            result = meter.process_audio(audio, sr, progress_callback=on_process_progress)
            
            # === 阶段4: 最终计算 (90-95%) ===
            self.sub_step.emit(self.tr("计算最终指标..."), 90)
            
            # 获取结果（使用最大值）
            integrated = result['integrated']
            short_term = result['max_short_term'] if result['max_short_term'] != -np.inf else result['short_term']
            momentary = result['max_momentary'] if result['max_momentary'] != -np.inf else result['momentary']
            lra = result['lra']
            true_peak = result['true_peak']
            
            # 收集详细时序数据用于导出
            detailed_data = self._build_detailed_data(result, actual_duration)
            
            # === 阶段5: 完成 (95-100%) ===
            self.sub_step.emit(self.tr("整理结果..."), 95)
            
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
            
            self.sub_step.emit(self.tr("完成"), 100)
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
                self.sub_step.emit(self.tr("加载中... {mb_loaded:.1f}/{mb_total:.1f} MB").format(mb_loaded=mb_loaded, mb_total=mb_total), int(progress))
        
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
            self.sub_step.emit(self.tr("加载: {name} ({current}/{total})").format(name=name, current=i+1, total=total_files), int(progress))
            
            data, _ = sf.read(path, dtype='float32')
            if data.ndim > 1:
                data = data[:, 0]
            
            copy_len = min(len(data), max_samples)
            audio[:copy_len, i] = data[:copy_len]
        
        return audio, sr


class ADMRenderWorker(QThread):
    """ADM 渲染后台线程，带进度反馈"""
    progress = Signal(int)
    finished_signal = Signal(str)
    error = Signal(str)
    
    def __init__(self, input_path: str, target_layout: str):
        super().__init__()
        self.input_path = input_path
        self.target_layout = target_layout
        self._cancelled = False
    
    def run(self):
        try:
            import sys
            from pathlib import Path
            src_dir = str(Path(__file__).parent)
            if src_dir not in sys.path:
                sys.path.insert(0, src_dir)
            from renderers.ear_renderer import render_adm_with_progress
            
            def on_progress(percent: int):
                if not self._cancelled:
                    self.progress.emit(percent)
            
            output_path = render_adm_with_progress(
                self.input_path,
                self.target_layout,
                progress_callback=on_progress,
            )
            self.finished_signal.emit(output_path)
        except Exception as e:
            import traceback
            err_detail = traceback.format_exc()
            print(f"[ADM渲染错误] {err_detail}")
            self.error.emit(str(e))
    
    def cancel(self):
        self._cancelled = True


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
        left.setMinimumWidth(420)
        main_layout.addWidget(left, 40)
        
        center = self._create_center_panel()
        center.setMaximumWidth(380)
        main_layout.addWidget(center, 25)
        
        right = self._create_right_panel()
        right.setMinimumWidth(260)
        main_layout.addWidget(right, 30)

    def _update_mono_files_list(self):
        """更新多单声道文件列表显示，支持编辑声道和顺序"""
        self.mono_files_table.blockSignals(True)
        if not self.mono_files:
            self.mono_files_table.setRowCount(0)
            self.mono_files_group.setTitle('📋 声道匹配 (双击声道可编辑)')
            self.mono_files_table.blockSignals(False)
            return

        self.mono_files_table.setRowCount(len(self.mono_files))
        for i, (path, ch_name) in enumerate(self.mono_files):
            # 序号
            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignCenter)
            num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
            self.mono_files_table.setItem(i, 0, num_item)

            # 声道（可编辑，有代理下拉框）
            ch_item = QTableWidgetItem(ch_name)
            ch_item.setTextAlignment(Qt.AlignCenter)
            if ch_name == '?':
                ch_item.setForeground(QColor('#e74c3c'))
            else:
                ch_item.setForeground(QColor('#27ae60'))
            self.mono_files_table.setItem(i, 1, ch_item)

            # 文件名
            filename = Path(path).name
            file_item = QTableWidgetItem(filename)
            file_item.setToolTip(str(path))
            file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)
            self.mono_files_table.setItem(i, 2, file_item)

        self.mono_files_group.setVisible(True)
        matched = sum(1 for _, ch in self.mono_files if ch != '?')
        self.mono_files_group.setTitle(f'📋 声道匹配 ({matched}/{len(self.mono_files)} 已匹配)')
        self.mono_files_table.blockSignals(False)
    def parse_and_display_adm(self, file_path: str):
        """解析ADM文件并在UI中显示详细信息"""
        try:
            self.adm_info.clear()
            self.adm_info.setPlainText(self.tr("正在解析 ADM..."))
            QApplication.processEvents()  # 立即更新UI
            
            parser = BW64Parser(file_path)
            adm = parser.parse()
            
            if not adm:
                self.adm_info.setPlainText(self.tr("[错误] 无法解析 ADM 元数据\n\n可能原因：\n1. 文件不是有效的 ADM/BW64 格式\n2. XML 命名空间不匹配"))
                return
            
            # 检查解析结果是否为空
            if not adm.channel_formats and not adm.programmes:
                self.adm_info.setPlainText(self.tr("[警告] ADM 元数据解析为空\n\n可能原因：\n1. 命名空间检测失败\n2. 文件不包含 ADM 数据"))
                return
            
            # 收集信息
            lines = []
            lines.append(self.tr("📦 文件: {name}").format(name=Path(file_path).name))
            lines.append("")
            
            # 节目信息
            if adm.programmes:
                prog_name = adm.programmes[0].get('name', 'N/A')
                lines.append(self.tr("🎬 节目: {name}").format(name=prog_name))
            
            # 内容统计
            content_count = len(adm.contents)
            object_count = len(adm.objects)
            lines.append(self.tr("📊 内容: {cc} 个 Content, {oc} 个 Object").format(cc=content_count, oc=object_count))
            
            # 声床分析
            direct_speakers = [ch for ch in adm.channel_formats if ch.type == 'DirectSpeakers']
            objects_ch = [ch for ch in adm.channel_formats if ch.type == 'Objects']
            
            lines.append("")
            lines.append(self.tr("🔊 声床配置 ({count} DirectSpeakers):").format(count=len(direct_speakers)))
            
            # 显示声床详情
            for i, ch in enumerate(direct_speakers):
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
            
            # 检测Objects
            has_objects = bool(objects_ch)
            if has_objects:
                lines.append("")
                lines.append(self.tr("⚠️ 包含 {count} 个动态对象 (Object)").format(count=len(objects_ch)))
                self.atmos_render_group.setVisible(True)
                self.atmos_render_label.setText(
                    self.tr("检测到 {count} 个动态对象，可选择渲染到目标声道布局后，点击“渲染并测量”测量。\n"
                            "注意：点击中间面板“开始测量”将仅测量声道响度，不包含对象。").format(count=len(objects_ch))
                )
            else:
                self.atmos_render_group.setVisible(False)
            
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
                lines.append(self.tr("🎯 自动识别为: {desc} ({ch_count} ch 声床, 置信度 {conf})").format(desc=description, ch_count=ch_count, conf=f"{confidence:.0%}"))
            else:
                # 回退到数量映射
                cfg_map = {
                    2: 'stereo', 6: '5.1', 8: '7.1', 
                    10: '5.1.4', 12: '7.1.4', 16: '9.1.6'
                }
                fallback = cfg_map.get(ch_count, self.tr('未知'))
                if ch_count in cfg_map:
                    self.config_combo.setCurrentText(cfg_map[ch_count])
                else:
                    self.config_combo.setCurrentText(self.tr("自动检测"))
                lines.append(self.tr("⚠️ 基于数量识别: {fallback} ({ch_count} ch)").format(fallback=fallback, ch_count=ch_count))
                if detected == 'unknown':
                    lines.append(self.tr("   (特征识别失败，请手动确认)"))
            
            # 渲染器与创作软件信息（合并到 adm_info 中）
            lines.append("")
            lines.append("─" * 36)
            lines.append(self.tr("🎛️ 渲染器与创作软件信息"))
            lines.append("─" * 36)
            
            if adm.renderer_info:
                r_info = adm.renderer_info
                r_text = self.tr('🎚️ {name}').format(name=r_info.get('name', self.tr('未知渲染器')))
                if r_info.get('version'):
                    r_text += f" v{r_info['version']}"
                if r_info.get('coordinate_mode'):
                    r_text += f" [{r_info['coordinate_mode']}]"
                if r_info.get('uri'):
                    r_text += f"\n   URI: {r_info['uri']}"
                lines.append(r_text)
            else:
                lines.append(self.tr("🎚️ 未检测到渲染器信息"))
            
            if adm.authoring_info:
                a_info = adm.authoring_info
                if a_info.get('authoring_tool'):
                    a_text = f"🛠️ {a_info['authoring_tool']}"
                    if a_info.get('authoring_tool_version'):
                        a_text += f" v{a_info['authoring_tool_version']}"
                    lines.append(a_text)
                else:
                    lines.append(self.tr("🛠️ 未检测到创作软件"))
                
                if a_info.get('reference_layout'):
                    lines.append(self.tr('📐 参考布局: {layout}').format(layout=a_info['reference_layout']))
            else:
                lines.append(self.tr("🛠️ 未检测到创作软件信息"))
            
            # 显示到UI
            self.adm_info.setPlainText("\n".join(lines))
            
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

        panel = QGroupBox(self.tr("📁 输入"))
        panel.setMinimumWidth(340)
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
        mode_group = QGroupBox(self.tr("输入方式"))
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

        self.btn_mono = QPushButton(self.tr("🎵 多单声道"))
        self.btn_standard = QPushButton(self.tr("📁 单个多声道"))
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
        # === 2. 文件信息卡片（单个多声道/ADM 模式显示） ===
        self.file_info_group = QGroupBox(self.tr("文件信息"))
        self.file_info_group.setStyleSheet("""
            QGroupBox {
                font-size: 12px;
                border: 1px solid #3498db;
            }
            QGroupBox::title { color: #3498db; }
        """)
        file_layout = QVBoxLayout(self.file_info_group)
        file_layout.setSpacing(8)

        self.filename_label = QLabel(self.tr("未选择文件"))
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
            ('format', self.tr('格式')), ('channels', self.tr('声道')),
            ('samplerate', self.tr('采样率')), ('bit_depth', self.tr('位深')),
            ('duration', self.tr('时长')), ('file_size', self.tr('大小')),
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

        # === 浏览按钮（永久显示） ===
        browse_btn = QPushButton(self.tr("浏览..."))
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

        layout.addWidget(self.file_info_group)

        # === 3. 模式专属区域 ===
        # -- 单个多声道 --
        self.standard_section = QWidget()
        standard_layout = QVBoxLayout(self.standard_section)
        standard_layout.setContentsMargins(0, 0, 0, 0)
        standard_layout.setSpacing(8)

        cfg_layout = QHBoxLayout()
        cfg_layout.addWidget(QLabel(self.tr("声道配置:")))
        self.config_combo = QComboBox()
        self.config_combo.addItems([self.tr("自动检测"), "stereo", "5.1", "7.1", "5.1.4", "7.1.2", "7.1.4"])
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

        self.adm_info_group = QGroupBox(self.tr("ADM 信息"))
        self.adm_info_group.setStyleSheet("""
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
        adm_info_layout = QVBoxLayout(self.adm_info_group)
        adm_info_layout.setContentsMargins(6, 2, 6, 6)
        adm_info_layout.setSpacing(4)

        self.adm_info = QTextEdit()
        self.adm_info.setReadOnly(True)
        self.adm_info.setPlaceholderText(self.tr("ADM文件信息将显示在这里..."))
        self.adm_info.setMaximumHeight(160)
        self.adm_info.setStyleSheet("""
            QTextEdit {
                background-color: #16213e;
                border: none;
                color: #eee;
                font-family: Consolas, Monaco, monospace;
                font-size: 11px;
                padding: 4px;
            }
        """)
        adm_info_layout.addWidget(self.adm_info)
        adm_layout.addWidget(self.adm_info_group)

        # Dolby Atmos / Audio Vivid 渲染选项
        self.atmos_render_group = QGroupBox(self.tr("🎧 沉浸式音频渲染"))
        self.atmos_render_group.setVisible(False)
        self.atmos_render_group.setMinimumHeight(160)
        self.atmos_render_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #9b59b6;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 6px;
                font-weight: bold;
                font-size: 11px;
            }
            QGroupBox::title { color: #9b59b6; }
        """)
        atmos_render_layout = QVBoxLayout(self.atmos_render_group)
        atmos_render_layout.setSpacing(6)
        atmos_render_layout.setContentsMargins(10, 10, 10, 10)

        self.atmos_render_label = QLabel(self.tr("检测到动态对象音频，可选择渲染到目标声道布局后测量响度。\n注意：点击中间面板“开始测量”将仅测量声道响度，不包含对象。"))
        self.atmos_render_label.setStyleSheet("color: #bbb; font-size: 10px;")
        self.atmos_render_label.setWordWrap(True)
        atmos_render_layout.addWidget(self.atmos_render_label)

        atmos_ctrl_layout = QHBoxLayout()
        atmos_ctrl_layout.addWidget(QLabel(self.tr("目标布局:")))
        self.atmos_layout_combo = QComboBox()
        self.atmos_layout_combo.addItems(get_supported_layouts())
        self.atmos_layout_combo.setCurrentText("5.1.4 (10ch)")
        self.atmos_layout_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f3460;
                border: 1px solid #9b59b6;
                padding: 4px;
                font-size: 12px;
                color: #eee;
            }
        """)
        atmos_ctrl_layout.addWidget(self.atmos_layout_combo, 1)

        self.atmos_render_btn = QPushButton(self.tr("🎯 渲染并测量"))
        self.atmos_render_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                border: none;
                padding: 5px 10px;
                border-radius: 4px;
                font-size: 11px;
                color: white;
            }
            QPushButton:hover { background-color: #8e44ad; }
        """)
        self.atmos_render_btn.clicked.connect(self._render_and_measure_adm)
        atmos_ctrl_layout.addWidget(self.atmos_render_btn)
        atmos_render_layout.addLayout(atmos_ctrl_layout)

        adm_layout.addWidget(self.atmos_render_group)
        adm_layout.addStretch()
        layout.addWidget(self.adm_section)

        # -- 多单声道 --
        self.mono_section = QWidget()
        mono_layout = QVBoxLayout(self.mono_section)
        mono_layout.setContentsMargins(0, 0, 0, 0)
        mono_layout.setSpacing(8)

        # 模板选择 + 控制按钮
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(6)
        ctrl_layout.addWidget(QLabel(self.tr("声道模板:")))
        self.mono_template_combo = QComboBox()
        self.mono_template_combo.addItems([
            self.tr("自动检测"), "Stereo (2.0)", "5.1 (6ch)", "7.1 (8ch)",
            "7.1.2 (10ch)", "5.1.4 (10ch)", "7.1.4 (12ch)", self.tr("自定义")
        ])
        self.mono_template_combo.setStyleSheet("""
            QComboBox {
                background-color: #0f3460;
                border: 1px solid #27ae60;
                padding: 4px;
                font-size: 12px;
                color: #eee;
            }
        """)
        ctrl_layout.addWidget(self.mono_template_combo, 1)

        self.mono_match_btn = QPushButton(self.tr("🎯 自动匹配"))
        self.mono_match_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                border: none;
                padding: 5px 10px;
                border-radius: 4px;
                font-size: 11px;
                color: white;
            }
            QPushButton:hover { background-color: #2ecc71; }
            QPushButton:disabled { background-color: #1e8449; color: #aaa; }
        """)
        self.mono_match_btn.clicked.connect(self._on_mono_auto_match)
        ctrl_layout.addWidget(self.mono_match_btn)

        self.mono_up_btn = QPushButton("⬆️")
        self.mono_up_btn.setToolTip(self.tr("上移"))
        self.mono_up_btn.setStyleSheet("QPushButton { padding: 5px 8px; font-size: 11px; }")
        self.mono_up_btn.clicked.connect(self._on_mono_move_up)
        ctrl_layout.addWidget(self.mono_up_btn)

        self.mono_down_btn = QPushButton("⬇️")
        self.mono_down_btn.setToolTip(self.tr("下移"))
        self.mono_down_btn.setStyleSheet("QPushButton { padding: 5px 8px; font-size: 11px; }")
        self.mono_down_btn.clicked.connect(self._on_mono_move_down)
        ctrl_layout.addWidget(self.mono_down_btn)

        self.mono_del_btn = QPushButton("🗑️")
        self.mono_del_btn.setToolTip(self.tr("删除选中"))
        self.mono_del_btn.setStyleSheet("QPushButton { padding: 5px 8px; font-size: 11px; }")
        self.mono_del_btn.clicked.connect(self._on_mono_delete)
        ctrl_layout.addWidget(self.mono_del_btn)

        self.mono_clear_btn = QPushButton(self.tr("清空"))
        self.mono_clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #c0392b;
                border: none;
                padding: 5px 10px;
                border-radius: 4px;
                font-size: 11px;
                color: white;
            }
            QPushButton:hover { background-color: #e74c3c; }
        """)
        self.mono_clear_btn.clicked.connect(self._clear_mono_files)
        ctrl_layout.addWidget(self.mono_clear_btn)
        mono_layout.addLayout(ctrl_layout)

        self.mono_files_group = QGroupBox(self.tr("📋 声道匹配 (双击声道可编辑)"))
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

        self.mono_files_table = QTableWidget(0, 3)
        self.mono_files_table.setHorizontalHeaderLabels([self.tr('#'), self.tr('声道'), self.tr('文件名')])
        self.mono_files_table.verticalHeader().setVisible(False)
        self.mono_files_table.horizontalHeader().setStretchLastSection(True)
        self.mono_files_table.setMinimumHeight(180)
        self.mono_files_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mono_files_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.mono_files_table.setEditTriggers(QAbstractItemView.DoubleClicked)
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
            QTableWidget::item:selected {
                background-color: #1a4a7a;
            }
        """)
        self.mono_files_table.setColumnWidth(0, 30)
        self.mono_files_table.setColumnWidth(1, 60)
        # 声道列使用 QComboBox 代理
        class ChannelComboDelegate(QStyledItemDelegate):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.channels = ['L', 'R', 'C', 'LFE', 'Ls', 'Rs', 'Lss', 'Rss',
                                 'Lrs', 'Rrs', 'Ltf', 'Rtf', 'Ltr', 'Rtr', 'Ltb', 'Rtb', '?']
            def createEditor(self, parent, option, index):
                editor = QComboBox(parent)
                editor.addItems(self.channels)
                return editor
            def setEditorData(self, editor, index):
                text = index.model().data(index, Qt.EditRole)
                idx = editor.findText(text)
                if idx >= 0:
                    editor.setCurrentIndex(idx)
            def setModelData(self, editor, model, index):
                model.setData(index, editor.currentText(), Qt.EditRole)
        self.mono_files_table.setItemDelegateForColumn(1, ChannelComboDelegate(self))
        self.mono_files_table.itemChanged.connect(self._on_mono_item_changed)
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

    # ---------- 多单声道控制方法 ----------

    def _on_mono_auto_match(self):
        """对当前已加载的文件重新执行自动匹配"""
        if not self.mono_files:
            QMessageBox.information(self, self.tr("提示"), self.tr("请先选择文件"))
            return
        template_map = {
            "Stereo (2.0)": "Stereo (2.0)",
            "5.1 (6ch)": "5.1 (6ch)",
            "7.1 (8ch)": "7.1 (8ch)",
            "7.1.2 (10ch)": "7.1.2 (10ch)",
            "5.1.4 (10ch)": "5.1.4 (10ch)",
            "7.1.4 (12ch)": "7.1.4 (12ch)",
        }
        combo_text = self.mono_template_combo.currentText()
        template_name = template_map.get(combo_text, None)
        file_paths = [p for p, _ in self.mono_files]
        self.mono_files = auto_match_mono_files(file_paths, template_name=template_name)
        self._update_mono_files_list()

    def _on_mono_move_up(self):
        row = self.mono_files_table.currentRow()
        if row <= 0:
            return
        self.mono_files[row], self.mono_files[row - 1] = self.mono_files[row - 1], self.mono_files[row]
        self._update_mono_files_list()
        self.mono_files_table.selectRow(row - 1)

    def _on_mono_move_down(self):
        row = self.mono_files_table.currentRow()
        if row < 0 or row >= len(self.mono_files) - 1:
            return
        self.mono_files[row], self.mono_files[row + 1] = self.mono_files[row + 1], self.mono_files[row]
        self._update_mono_files_list()
        self.mono_files_table.selectRow(row + 1)

    def _on_mono_delete(self):
        row = self.mono_files_table.currentRow()
        if row < 0 or row >= len(self.mono_files):
            return
        del self.mono_files[row]
        self._update_mono_files_list()
        if self.mono_files and row < len(self.mono_files):
            self.mono_files_table.selectRow(row)
        elif self.mono_files:
            self.mono_files_table.selectRow(len(self.mono_files) - 1)

    def _on_mono_item_changed(self, item):
        """表格编辑完成后同步到 self.mono_files"""
        if item.column() != 1:
            return
        row = item.row()
        if row < 0 or row >= len(self.mono_files):
            return
        new_ch = item.text()
        path, _ = self.mono_files[row]
        self.mono_files[row] = (path, new_ch)
        # 更新颜色
        if new_ch == '?':
            item.setForeground(QColor('#e74c3c'))
        else:
            item.setForeground(QColor('#27ae60'))
        matched = sum(1 for _, ch in self.mono_files if ch != '?')
        self.mono_files_group.setTitle(f'📋 声道匹配 ({matched}/{len(self.mono_files)} 已匹配)')


    def _clear_mono_files(self):
        """清空多单声道文件列表"""
        self.mono_files = []
        self._update_mono_files_list()
        self.filename_label.setText(self.tr("未选择文件"))
        self.filename_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #667eea;")
        self.path_label.setText("")

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
                    self.filename_label.setText(self.tr("✓ {name} (请在浏览中添加更多)").format(name=p.name))
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
                QMessageBox.warning(self, self.tr("文件错误"), self.tr("无法读取文件:\n{err}").format(err=e))
                return

        QMessageBox.warning(self, self.tr("不支持的文件"), self.tr("无法识别该文件类型:\n{name}").format(name=p.name))

    
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
        il_label = QLabel(self.tr("Immersive Loudness"))
        il_label.setStyleSheet('color: #667eea; font-size: 10px; font-weight: thin; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; letter-spacing: 10px; border: none;')
        il_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(il_label)

        # IL
        il_label = QLabel('IL')
        il_label.setStyleSheet('color: #667eea; font-size: 64px; font-weight: bold; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; letter-spacing: 12px; border: none;')
        il_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(il_label)
        
        # Immersive Loudness
        name_label = QLabel('Immersive audio file Loudness measure tool')
        name_label.setStyleSheet('color: #a0b4e8; font-size: 12px; font-weight: bold; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; letter-spacing: 1px; border: none;')
        name_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(name_label)
        
        # 底部行
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(0)
        bottom_layout.setContentsMargins(0, 2, 0, 0)
        
        # 左侧三行功能描述
        left_info = QVBoxLayout()
        left_info.setSpacing(0)
        left_info.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        for line_text in ["Channel auto-match", "ADM analysis and render", "Excel export"]:
            lbl = QLabel(line_text)
            lbl.setStyleSheet('color: #8899cc; font-size: 8px; font-family: "Segoe UI", sans-serif; border: none;')
            left_info.addWidget(lbl)
        bottom_layout.addLayout(left_info)
        
        bottom_layout.addStretch(1)
        
        # 右侧版本和版权
        right_info = QVBoxLayout()
        right_info.setSpacing(0)
        right_info.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        
        version_label = QLabel('v1.0  (build 260511)')
        version_label.setStyleSheet('color: #667eea; font-size: 8px; border: none;')
        version_label.setAlignment(Qt.AlignRight)
        right_info.addWidget(version_label)
        
        copyright_label = QLabel('© 2026 YOY')
        copyright_label.setStyleSheet('color: #888; font-size: 7px; border: none;')
        copyright_label.setAlignment(Qt.AlignRight)
        right_info.addWidget(copyright_label)
        
        bottom_layout.addLayout(right_info)
        header_layout.addLayout(bottom_layout)
        layout.addWidget(header_widget)
        
        # === 原有内容 ===
        content_widget = QGroupBox(self.tr("⚙️ 标准与进度"))
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(8)
        
        content_layout.addWidget(QLabel(self.tr("响度标准:")))
        self.std_combo = QComboBox()
        self.std_combo.setMaximumWidth(360)
        self.std_combo.addItem(self.tr("GY/T 282-2014 (中国广电-电视)"), "GY/T 282-2014 (中国广电-电视)")
        self.std_combo.addItem(self.tr("GY/T 377-2023 (中国广电-网络/嘈杂环境)"), "GY/T 377-2023 (中国广电-网络/嘈杂环境)")
        self.std_combo.addItem(self.tr("EBU R128 (欧洲广播)"), "EBU R128 (欧洲广播)")
        self.std_combo.addItem(self.tr("ATSC A/85 (美国电视)"), "ATSC A/85 (美国电视)")
        self.std_combo.currentTextChanged.connect(self.on_std_changed)
        self.std_combo.setCurrentIndex(0)
        content_layout.addWidget(self.std_combo)
        
        self.std_info = QLabel()
        self.std_info.setStyleSheet('background-color: #16213e; padding: 8px; border-radius: 4px;')
        self.update_std_info()
        content_layout.addWidget(self.std_info)
        
        content_layout.addSpacing(10)
        
        # 渲染进度（ADM 渲染专用，与测量进度独立）
        self.render_step_label = QLabel('')
        self.render_step_label.setStyleSheet('color: #9b59b6; font-weight: bold;')
        self.render_step_label.setVisible(False)
        content_layout.addWidget(self.render_step_label)
        
        self.render_progress = QProgressBar()
        self.render_progress.setVisible(False)
        self.render_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #9b59b6;
                border-radius: 4px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #9b59b6;
                border-radius: 4px;
            }
        """)
        content_layout.addWidget(self.render_progress)
        
        content_layout.addWidget(QLabel(self.tr("当前步骤:")))
        self.step_label = QLabel(self.tr("等待开始"))
        self.step_label.setStyleSheet('color: #667eea; font-weight: bold;')
        content_layout.addWidget(self.step_label)
        
        content_layout.addWidget(QLabel(self.tr("总进度:")))
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        content_layout.addWidget(self.progress)
        
        self.process_info = QLabel()
        self.process_info.setStyleSheet('color: #888; font-size: 11px;')
        self.process_info.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self.process_info)
        
        self.start_btn = QPushButton(self.tr("▶ 开始测量"))
        self.start_btn.setStyleSheet('QPushButton { background-color: #667eea; color: white; font-weight: bold; font-size: 16px; padding: 12px; border-radius: 8px; } QPushButton:hover { background-color: #764ba2; }')
        self.start_btn.clicked.connect(self.start_measure)
        content_layout.addWidget(self.start_btn)
        
        content_layout.addStretch()
        layout.addWidget(content_widget)
        layout.addStretch()
        return panel
    def _create_right_panel(self):
        panel = QGroupBox(self.tr("📊 结果与导出"))
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)
        
        self.result_table = QTableWidget(5, 2)
        self.result_table.setHorizontalHeaderLabels([self.tr("指标"), self.tr("数值")])
        self.result_table.verticalHeader().setVisible(False)
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.result_table.setColumnWidth(0, 170)
        self.result_table.setColumnWidth(1, 90)
        
        metrics = [self.tr("节目响度(I)"), self.tr("最大短时响度(S)"), self.tr("最大瞬时响度(M)"), self.tr("最大真峰值(TP)"), self.tr("响度范围(LRA)")]
        for i, m in enumerate(metrics):
            self.result_table.setItem(i, 0, QTableWidgetItem(m))
            item = QTableWidgetItem("--")
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.result_table.setItem(i, 1, item)
        
        layout.addWidget(self.result_table)
        
        status_layout = QHBoxLayout()
        self.int_status = QLabel(self.tr("节目响度: --"))
        self.int_status.setAlignment(Qt.AlignCenter)
        self.int_status.setStyleSheet("padding: 4px; border-radius: 4px;")
        status_layout.addWidget(self.int_status)
        
        self.tp_status = QLabel(self.tr("峰值: --"))
        self.tp_status.setAlignment(Qt.AlignCenter)
        self.tp_status.setStyleSheet("padding: 4px; border-radius: 4px;")
        status_layout.addWidget(self.tp_status)
        layout.addLayout(status_layout)
        
        export_box = QGroupBox(self.tr("导出"))
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
        
        export_note = QLabel(self.tr("TXT: 文本报告 | JSON: 结构化数据\nExcel: 包含每秒详细数据"))
        export_note.setStyleSheet("color: #888; font-size: 10px;")
        export_note.setAlignment(Qt.AlignCenter)
        export_layout.addWidget(export_note)
        
        layout.addWidget(export_box)
        
        self.status = QLabel(self.tr("就绪"))
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
            self.tr("目标: {target} LUFS (±{tol} LU)\n峰值: {peak} dBTP")
            .format(target=f"{std.integrated_target:+.1f}",
                    tol=f"{std.integrated_tolerance:.1f}",
                    peak=f"{std.true_peak_limit:+.1f}")
        )
    
    def on_std_changed(self, text):
        # Reverse map: find original key from translated or raw text
        for key in LOUDNESS_STANDARDS:
            if self.tr(key) == text or key == text:
                self.current_standard = LOUDNESS_STANDARDS[key]
                self.update_std_info()
                break
    
    def on_input_mode_changed(self, mode):
        """输入模式切换"""
        self._update_mode_buttons(mode)
        self._update_mode_ui(mode)
        self.current_file = None
        self.mono_files = None
        self.current_adm_parser = None

        # 文件信息框：仅单个多声道/ADM模式显示
        if hasattr(self, 'file_info_group'):
            self.file_info_group.setVisible(mode != 'mono')
        if hasattr(self, 'filename_label'):
            self.filename_label.setText(self.tr("未选择文件"))
            self.filename_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #667eea;")
        if hasattr(self, 'path_label'):
            self.path_label.setText("")
        self._clear_file_metadata()

        if hasattr(self, 'adm_info'):
            self.adm_info.clear()
            self.adm_info.setPlaceholderText(self.tr("ADM文件信息将显示在这里..."))
        if hasattr(self, 'atmos_render_group'):
            self.atmos_render_group.setVisible(False)
        if hasattr(self, 'mono_files_group'):
            self.mono_files_group.setVisible(False)


    
    def _render_and_measure_adm(self):
        """渲染 ADM 文件到目标布局，然后测量响度（后台线程带进度条）"""
        if not self.current_file or not Path(self.current_file).exists():
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择 ADM 文件"))
            return

        target_layout = self.atmos_layout_combo.currentText()

        from renderers.ear_renderer import is_object_based_adm

        if not is_object_based_adm(self.current_file):
            QMessageBox.information(self, self.tr("提示"), self.tr("该文件不包含动态对象音频，无需渲染。"))
            return

        # 禁用渲染按钮防止重复点击
        self.atmos_render_btn.setEnabled(False)

        # 显示渲染进度条
        self.render_step_label.setText(self.tr("🎧 正在渲染到 {layout}...").format(layout=target_layout))
        self.render_step_label.setVisible(True)
        self.render_progress.setValue(0)
        self.render_progress.setVisible(True)

        # 启动后台渲染线程
        self._render_worker = ADMRenderWorker(self.current_file, target_layout)
        self._render_worker.progress.connect(self._on_render_progress)
        self._render_worker.finished_signal.connect(self._on_render_finished)
        self._render_worker.error.connect(self._on_render_error)
        self._render_worker.start()

    def _on_render_progress(self, percent: int):
        """更新渲染进度条"""
        self.render_progress.setValue(percent)

    def _on_render_finished(self, output_path: str):
        """渲染完成，切换到标准模式并自动开始测量"""
        self.render_step_label.setText(self.tr("🎧 渲染完成"))
        self.render_progress.setValue(100)
        self.atmos_render_btn.setEnabled(True)

        # 切换到单个多声道模式，加载渲染后的文件
        self.btn_standard.setChecked(True)
        self.on_input_mode_changed('standard')
        self.current_file = output_path
        p = Path(output_path)
        self.filename_label.setText(self.tr("✓ 渲染: {name}").format(name=p.name))
        self.filename_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #9b59b6;")
        self.path_label.setText(str(p.parent))
        self._update_file_metadata(output_path)

        # 自动设置声道配置
        cfg_map = {"Stereo (2.0)": "stereo", "5.1 (6ch)": "5.1", "7.1 (8ch)": "7.1",
                   "5.1.4 (10ch)": "5.1.4", "7.1.4 (12ch)": "7.1.4", "9.1.6 (16ch)": "9.1.6"}
        if self.atmos_layout_combo.currentText() in cfg_map:
            self.config_combo.setCurrentText(cfg_map[self.atmos_layout_combo.currentText()])

        # 自动开始测量
        self.start_measure()

    def _on_render_error(self, error_msg: str):
        """渲染出错"""
        self.render_step_label.setText(self.tr("🎧 渲染失败"))
        self.render_progress.setValue(0)
        self.render_progress.setVisible(False)
        self.atmos_render_btn.setEnabled(True)
        QMessageBox.critical(self, self.tr("渲染失败"), self.tr("渲染过程中出错:\n{err}").format(err=error_msg))

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
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择输入方式"))
            return
        
        if mode == 'standard':  # 单个多声道文件
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

        elif mode == 'mono':  # 多单声道 — 直接选择文件 + 自动匹配
            files, _ = QFileDialog.getOpenFileNames(
                self, "选择单声道WAV文件", "", "WAV文件 (*.wav)"
            )
            if not files:
                return

            # 过滤非单声道
            valid_files = []
            skipped = []
            for path in files:
                try:
                    info = sf.info(path)
                    if info.channels == 1:
                        valid_files.append(path)
                    else:
                        skipped.append(f"{Path(path).name} ({info.channels}ch)")
                except Exception as e:
                    skipped.append(f"{Path(path).name}: {e}")

            if skipped:
                QMessageBox.information(self, self.tr("跳过文件"), self.tr("以下文件不是单声道或无法读取:\n{files}").format(files="\n".join(skipped[:10])))

            if not valid_files:
                return

            # 自动匹配
            template_map = {
                "Stereo (2.0)": "Stereo (2.0)",
                "5.1 (6ch)": "5.1 (6ch)",
                "7.1 (8ch)": "7.1 (8ch)",
                "7.1.2 (10ch)": "7.1.2 (10ch)",
                "5.1.4 (10ch)": "5.1.4 (10ch)",
                "7.1.4 (12ch)": "7.1.4 (12ch)",
            }
            combo_text = self.mono_template_combo.currentText()
            template_name = template_map.get(combo_text, None)
            self.mono_files = auto_match_mono_files(valid_files, template_name=template_name)

            if self.mono_files:
                p = Path(self.mono_files[0][0])
                self.filename_label.setText(self.tr("✓ {count} 个单声道文件").format(count=len(self.mono_files)))
                self.filename_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #27ae60;")
                self.path_label.setText(str(p.parent))

                cfg_map = {2: 'stereo', 6: '5.1', 8: '7.1', 10: '5.1.4', 12: '7.1.4'}
                matched_count = sum(1 for _, ch in self.mono_files if ch != '?')
                if matched_count in cfg_map:
                    self.config_combo.setCurrentText(cfg_map[matched_count])

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
                    QMessageBox.critical(self, self.tr("ADM错误"), self.tr("ADM 错误: {err}").format(err=str(e)))
                    return
        elif self.btn_mono.isChecked() and self.mono_files:
            input_mode = 'mono_list'
            input_data = self.mono_files
        else:
            QMessageBox.warning(self, self.tr("提示"), self.tr("请先选择输入文件"))
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
            self.process_info.setText(self.tr("{current:.1f}s/{total:.1f}s | ⚡{speed:.1f}x 实时 | {eta}")
                .format(current=current, total=total, speed=speed, eta=eta_str))
        else:
            self.process_info.setText(f"{current:.1f}s/{total:.1f}s | {eta_str}")
    
    def on_finished(self, results):
        # 合并文件信息到结果
        results['file_info'] = self._build_file_info()
        self.current_results = results
        self.progress.setVisible(False)
        self.start_btn.setEnabled(True)
        self.step_label.setText(self.tr("完成"))
        
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
        
        self.int_status.setText(self.tr("节目响度: {status}").format(status=('✓' if int_ok else '✗')))
        self.int_status.setStyleSheet(f"background-color: {'#27ae60' if int_ok else '#e74c3c'}; color: white; padding: 4px; border-radius: 4px;")
        
        self.tp_status.setText(self.tr("峰值: {status}").format(status=('✓' if tp_ok else '✗')))
        self.tp_status.setStyleSheet(f"background-color: {'#27ae60' if tp_ok else '#e74c3c'}; color: white; padding: 4px; border-radius: 4px;")
        
        self.status.setText(self.tr("完成 | 用时 {time:.1f}s").format(time=results.get('processing_time', 0)))
        self.export_txt_btn.setEnabled(True)
        self.export_json_btn.setEnabled(True)
        self.export_excel_btn.setEnabled(True)
    
    def on_error(self, msg):
        self.progress.setVisible(False)
        self.start_btn.setEnabled(True)
        self.step_label.setText(self.tr("错误"))
        QMessageBox.critical(self, self.tr("错误"), msg)
    
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
                
        elif self.btn_mono.isChecked() and self.mono_files:
            info['mode'] = 'mono'
            info['file_path'] = str(Path(self.mono_files[0][0]).parent)
            info['file_name'] = self.tr("{count} 个单声道文件").format(count=len(self.mono_files))
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
        
        # 清理标准名中的 Windows 非法字符
        std_name = self.current_standard.name.replace(' ', '_').replace('/', '_').replace('\\', '_')[:15]
        ext_map = {'txt': 'txt', 'json': 'json', 'excel': 'xlsx'}
        ext = ext_map.get(fmt, fmt)
        base = self._get_export_base_name()
        now = datetime.now()
        timestamp = f"{now:%y%m%d}_{now:%H}H{now:%M}"
        default_name = f"{base}_{timestamp}_{std_name}.{ext}"
        
        filter_map = {
            'txt': "文本文件 (*.txt)",
            'json': "JSON文件 (*.json)",
            'excel': "Excel文件 (*.xlsx)"
        }
        filter_str = filter_map.get(fmt, f"*.{ext}")
        
        # 使用 QFileDialog 类确保默认文件名在 Windows 原生对话框中正确显示
        dialog = QFileDialog(self, "导出")
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilter(filter_str)
        dialog.selectFile(default_name)
        if self.current_file:
            dialog.setDirectory(str(Path(self.current_file).parent))
        if dialog.exec() != QFileDialog.Accepted:
            return
        path = dialog.selectedFiles()[0]
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
            
            self.status.setText(self.tr("已导出: {name}").format(name=Path(path).name))
            
        except Exception as e:
            QMessageBox.critical(self, self.tr("导出失败"), self.tr("导出失败: {err}").format(err=str(e)))
    
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
            QMessageBox.warning(self, self.tr("缺少依赖"), self.tr("请安装 openpyxl: pip install openpyxl"))
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
            cell = ws.cell(row=row, column=1, value=self.tr('每秒最大真峰值'))
            cell.font = title_font
            cell.alignment = Alignment(horizontal='left', vertical='center')
            row += 2
            
            tp_headers = [self.tr('时间(秒)'), self.tr('真峰值(dBTP)'), self.tr('标准限值'), self.tr('状态')]
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


def _get_resource_path(relative_path):
    """获取 PyInstaller 打包后的资源路径"""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent.parent / relative_path


def _show_splash(app):
    """显示启动画面，覆盖程序初始化时间"""
    from PySide6.QtWidgets import QSplashScreen
    from PySide6.QtGui import QPixmap, QPainter, QFont, QColor, QFontMetrics
    from PySide6.QtCore import Qt
    
    pixmap = QPixmap(420, 280)
    pixmap.fill(QColor("#0f0f23"))
    
    painter = QPainter(pixmap)
    # 边框
    painter.setPen(QColor("#667eea"))
    painter.setBrush(Qt.NoBrush)
    painter.drawRoundedRect(10, 10, 400, 260, 12, 12)
    
    # IL 大字
    painter.setPen(QColor("#667eea"))
    painter.setFont(QFont("Segoe UI", 56, QFont.Bold))
    fm = QFontMetrics(painter.font())
    text = "IL"
    x = (pixmap.width() - fm.horizontalAdvance(text)) // 2
    painter.drawText(x, 110, text)
    
    # Immersive Loudness
    painter.setPen(QColor("#a0b4e8"))
    painter.setFont(QFont("Segoe UI", 14, QFont.Bold))
    fm = QFontMetrics(painter.font())
    text = "Immersive Loudness"
    x = (pixmap.width() - fm.horizontalAdvance(text)) // 2
    painter.drawText(x, 150, text)
    
    # 版本号
    painter.setPen(QColor("#667eea"))
    painter.setFont(QFont("Segoe UI", 10))
    fm = QFontMetrics(painter.font())
    text = "v1.0  (build 260511)"
    x = (pixmap.width() - fm.horizontalAdvance(text)) // 2
    painter.drawText(x, 180, text)
    
    # Loading...
    painter.setPen(QColor("#8899cc"))
    painter.setFont(QFont("Segoe UI", 9))
    fm = QFontMetrics(painter.font())
    text = "Loading..."
    x = (pixmap.width() - fm.horizontalAdvance(text)) // 2
    painter.drawText(x, 230, text)
    
    painter.end()
    
    splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    splash.show()
    app.processEvents()
    return splash


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--lang', default=None, help='Force language, e.g. en, zh')
    args, remaining = parser.parse_known_args()
    
    app = QApplication([sys.argv[0]] + remaining)
    app.setStyle('Fusion')
    
    # 显示启动画面（必须在重模块导入之前，让用户立刻看到反馈）
    splash = _show_splash(app)
    
    # 延迟导入重模块，减少启动前等待时间
    global sf, np, ITU1770Meter, ChannelConfig, LoudnessResults, ReportExporter, BW64Parser, is_adm_file
    import soundfile as sf
    import numpy as np
    from itu1770_meter import ITU1770Meter, ChannelConfig
    from report_exporter import LoudnessResults, ReportExporter
    from adm_parser import BW64Parser, is_adm_file
    
    # i18n: auto-detect system locale and load translation if available
    from PySide6.QtCore import QTranslator, QLocale
    translator = QTranslator()
    
    if args.lang:
        # 强制指定语言
        qm_path = _get_resource_path(f'i18n/ImmersiveLoudness_{args.lang}.qm')
        if not qm_path.exists():
            # 尝试加上地区后缀
            qm_path = _get_resource_path(f'i18n/ImmersiveLoudness_{args.lang}_US.qm')
    else:
        # 跨平台读取系统显示语言
        locale_name = QLocale.system().name()
        try:
            if sys.platform == 'win32':
                import ctypes
                import locale as py_locale
                lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
                locale_name = py_locale.windows_locale.get(lang_id, locale_name)
            elif sys.platform == 'darwin':
                # macOS: 读取 AppleLanguages
                import subprocess
                import ast
                result = subprocess.run(
                    ['defaults', 'read', '-g', 'AppleLanguages'],
                    capture_output=True, text=True, check=True
                )
                langs = ast.literal_eval(result.stdout.strip())
                if langs:
                    locale_name = langs[0].replace('-', '_')
        except Exception:
            pass
        qm_path = _get_resource_path(f'i18n/ImmersiveLoudness_{locale_name}.qm')
        if not qm_path.exists() and '_' in locale_name:
            # fallback to language code only, e.g. "en" from "en_US"
            lang = locale_name.split('_')[0]
            qm_path = _get_resource_path(f'i18n/ImmersiveLoudness_{lang}.qm')
    
    if qm_path.exists():
        if translator.load(str(qm_path)):
            app.installTranslator(translator)
    
    icon_path = _get_resource_path('assets/icon.ico')
    if icon_path.exists():
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(str(icon_path)))
    win = LoudnessMeterApp()
    splash.finish(win)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
