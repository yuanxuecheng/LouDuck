"""
mono_channel_matcher.py — 智能声道匹配模块

从 main_gui.py 独立提取，保留原始智能声道匹配算法的完整实现。
支持：
- 多单声道 WAV 文件的智能声道识别
- iXML 元数据读取
- 点号分隔声道标识（如 2005.L.wav）
- 正则匹配与模糊匹配
- 5.1 / 7.1 / 5.1.4 / 7.1.4 等配置模板
"""

import re
from pathlib import Path
from typing import List, Tuple, Optional, Dict

import soundfile as sf

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QListWidget, QLineEdit, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


# 声道配置模板 - 改进版，支持多种命名变体
CHANNEL_TEMPLATES = {
    "Stereo (2.0)": {
        "channels": ["L", "R"],
        "patterns": [
            r"(^|[^a-zA-Z.])(L|Left|FL|Front[_-]?Left)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(R|Right|FR|Front[_-]?Right)([^a-zA-Z0-9]|$)"
        ]
    },
    "5.1 (6ch)": {
        "channels": ["L", "R", "C", "LFE", "Ls", "Rs"],
        "patterns": [
            r"(^|[^a-zA-Z.])(L|Left|FL|Front[_-]?Left)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(R|Right|FR|Front[_-]?Right)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(C|Center|Centre|FC|Front[_-]?Center)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(LFE|Lfe|Sub|Subwoofer|SW)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Ls|LS|Lss|Lsr|Left[_-]?Surround|Left[_-]?Rear|Surround[_-]?Left|SL|BL|Back[_-]?Left|Lrs)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Rs|RS|Rss|Rsr|Right[_-]?Surround|Right[_-]?Rear|Surround[_-]?Right|SR|BR|Back[_-]?Right|Rrs)([^a-zA-Z0-9]|$)"
        ]
    },
    "7.1 (8ch)": {
        "channels": ["L", "R", "C", "LFE", "Lss", "Rss", "Lrs", "Rrs"],
        "patterns": [
            r"(^|[^a-zA-Z.])(L|Left|FL|Front[_-]?Left)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(R|Right|FR|Front[_-]?Right)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(C|Center|Centre|FC|Front[_-]?Center)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(LFE|Lfe|Sub|Subwoofer|SW)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Lss|LSs|Left[_-]?Side|Side[_-]?Left|SL|Left[_-]?Side[_-]?Surround)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Rss|RSs|Right[_-]?Side|Side[_-]?Right|SR|Right[_-]?Side[_-]?Surround)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Lrs|LRs|Left[_-]?Rear|Rear[_-]?Left|LR|Back[_-]?Left|BL|Left[_-]?Back|Lsr)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Rrs|RRs|Right[_-]?Rear|Rear[_-]?Right|RR|Back[_-]?Right|BR|Right[_-]?Back|Rsr)([^a-zA-Z0-9]|$)"
        ]
    },
    "7.1.2 (10ch)": {
        "channels": ["L", "R", "C", "LFE", "Lss", "Rss", "Lrs", "Rrs", "Ltf", "Rtf"],
        "patterns": [
            r"(^|[^a-zA-Z.])(L|Left|FL|Front[_-]?Left)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(R|Right|FR|Front[_-]?Right)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(C|Center|Centre|FC|Front[_-]?Center)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(LFE|Lfe|Sub|Subwoofer|SW)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Lss|LSs|Left[_-]?Side|Side[_-]?Left|SL|Left[_-]?Side[_-]?Surround)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Rss|RSs|Right[_-]?Side|Side[_-]?Right|SR|Right[_-]?Side[_-]?Surround)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Lrs|LRs|Left[_-]?Rear|Rear[_-]?Left|LR|Back[_-]?Left|BL|Left[_-]?Back|Lsr)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Rrs|RRs|Right[_-]?Rear|Rear[_-]?Right|RR|Back[_-]?Right|BR|Right[_-]?Back|Rsr)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Ltf|LtF|Left[_-]?Top[_-]?Front|Top[_-]?Front[_-]?Left|TFL|Lft|Left[_-]?Front[_-]?Top)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Rtf|RtF|Right[_-]?Top[_-]?Front|Top[_-]?Front[_-]?Right|TFR|Rft|Right[_-]?Front[_-]?Top)([^a-zA-Z0-9]|$)"
        ]
    },
    "5.1.4 (10ch)": {
        "channels": ["L", "R", "C", "LFE", "Ls", "Rs", "Ltf", "Rtf", "Ltr", "Rtr"],
        "patterns": [
            r"(^|[^a-zA-Z.])(L|Left|FL|Front[_-]?Left)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(R|Right|FR|Front[_-]?Right)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(C|Center|Centre|FC|Front[_-]?Center)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(LFE|Lfe|Sub|Subwoofer|SW)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Ls|LS|Lss|Lsr|Left[_-]?Surround|Left[_-]?Rear|Surround[_-]?Left|SL|BL|Back[_-]?Left|Lrs)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Rs|RS|Rss|Rsr|Right[_-]?Surround|Right[_-]?Rear|Surround[_-]?Right|SR|BR|Back[_-]?Right|Rrs)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Ltf|LtF|Left[_-]?Top[_-]?Front|Top[_-]?Front[_-]?Left|TFL|Lft|Left[_-]?Front[_-]?Top)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Rtf|RtF|Right[_-]?Top[_-]?Front|Top[_-]?Front[_-]?Right|TFR|Rft|Right[_-]?Front[_-]?Top)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Ltr|LtR|Left[_-]?Top[_-]?Rear|Top[_-]?Rear[_-]?Left|TRL|Lrt|Left[_-]?Rear[_-]?Top|Ltb|Left[_-]?Top[_-]?Back)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Rtr|RtR|Right[_-]?Top[_-]?Rear|Top[_-]?Rear[_-]?Right|TRR|Rrt|Right[_-]?Rear[_-]?Top|Rtb|Right[_-]?Top[_-]?Back)([^a-zA-Z0-9]|$)"
        ]
    },
    "7.1.4 (12ch)": {
        "channels": ["L", "R", "C", "LFE", "Lss", "Rss", "Lrs", "Rrs", "Ltf", "Rtf", "Ltb", "Rtb"],
        "patterns": [
            r"(^|[^a-zA-Z.])(L|Left|FL|Front[_-]?Left)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(R|Right|FR|Front[_-]?Right)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(C|Center|Centre|FC|Front[_-]?Center)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(LFE|Lfe|Sub|Subwoofer|SW)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Lss|LSs|Left[_-]?Side|Side[_-]?Left|SL|Left[_-]?Side[_-]?Surround)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Rss|RSs|Right[_-]?Side|Side[_-]?Right|SR|Right[_-]?Side[_-]?Surround)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Lrs|LRs|Left[_-]?Rear|Rear[_-]?Left|LR|Back[_-]?Left|BL|Left[_-]?Back|Lsr)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Rrs|RRs|Right[_-]?Rear|Rear[_-]?Right|RR|Back[_-]?Right|BR|Right[_-]?Back|Rsr)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Ltf|LtF|Left[_-]?Top[_-]?Front|Top[_-]?Front[_-]?Left|TFL|Lft)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Rtf|RtF|Right[_-]?Top[_-]?Front|Top[_-]?Front[_-]?Right|TFR|Rft)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Ltb|LtB|Left[_-]?Top[_-]?Back|Top[_-]?Back[_-]?Left|TBL|Lbt)([^a-zA-Z0-9]|$)",
            r"(^|[^a-zA-Z.])(Rtb|RtB|Right[_-]?Top[_-]?Back|Top[_-]?Back[_-]?Right|TBR|Rbt)([^a-zA-Z0-9]|$)"
        ]
    },
}


def _read_wav_channel_label(filepath: str) -> str:
    """从 WAV/BWF 文件读取 iXML 声道标签"""
    try:
        with sf.SoundFile(filepath) as f:
            extra = f.extra_info
        if not extra or "<BWFXML>" not in extra:
            return ""
        import xml.etree.ElementTree as ET
        root = ET.fromstring(extra)
        for track_list in root.findall(".//TRACK_LIST"):
            for track in track_list.findall("TRACK"):
                name = track.findtext("NAME", "").strip()
                if name:
                    return name
        return ""
    except Exception:
        return ""


def _extract_channel_id(filename: str) -> str:
    """从文件名提取声道标识，支持常见变体"""
    dot_parts = filename.split(".")
    if len(dot_parts) > 1:
        suffix = dot_parts[-1].upper()
        ch_map = {
            'L': 'L', 'LEFT': 'L', 'FL': 'L',
            'R': 'R', 'RIGHT': 'R', 'FR': 'R',
            'C': 'C', 'CENTER': 'C', 'CENTRE': 'C', 'FC': 'C',
            'LFE': 'LFE', 'SUB': 'LFE', 'SW': 'LFE', 'LFE1': 'LFE', 'LFE2': 'LFE',
            'LS': 'Ls', 'LSS': 'Lss', 'SL': 'Ls', 'SSL': 'Lss',
            'RS': 'Rs', 'RSS': 'Rss', 'SR': 'Rs', 'SSR': 'Rss',
            'LRS': 'Lrs', 'LR': 'Lrs', 'BL': 'Lrs', 'LSR': 'Lrs', 'SRL': 'Lrs',
            'RRS': 'Rrs', 'RR': 'Rrs', 'BR': 'Rrs', 'RSR': 'Rrs', 'SRR': 'Rrs',
            'LTF': 'Ltf', 'TFL': 'Ltf', 'LFT': 'Ltf',
            'RTF': 'Rtf', 'TFR': 'Rtf', 'RFT': 'Rtf',
            'LTR': 'Ltr', 'TRL': 'Ltr', 'LRT': 'Ltr',
            'RTR': 'Rtr', 'TRR': 'Rtr', 'RRT': 'Rtr',
            'LTB': 'Ltb', 'TBL': 'Ltb', 'LBT': 'Ltb',
            'RTB': 'Rtb', 'TBR': 'Rtb', 'RBT': 'Rtb',
        }
        if suffix in ch_map:
            return ch_map[suffix]
    n = filename.upper()
    patterns = [
        (r'(^|[^A-Za-z.])(LFE|SUB|SUBWOOFER|SW)([^A-Za-z.]|$)', 'LFE'),
        (r'(^|[^A-Za-z.])(LTR|TRL)([^A-Za-z.]|$)', 'Ltr'),
        (r'(^|[^A-Za-z.])(RTR|TRR)([^A-Za-z.]|$)', 'Rtr'),
        (r'(^|[^A-Za-z.])(LTB|TBL|LEFT.*TOP.*BACK|BACK.*TOP.*LEFT|TOP.*BACK.*LEFT)([^A-Za-z.]|$)', 'Ltb'),
        (r'(^|[^A-Za-z.])(RTB|TBR|RIGHT.*TOP.*BACK|BACK.*TOP.*RIGHT|TOP.*BACK.*RIGHT)([^A-Za-z.]|$)', 'Rtb'),
        (r'(^|[^A-Za-z.])(LTF|TFL|LEFT.*TOP.*FRONT|FRONT.*TOP.*LEFT|TOP.*FRONT.*LEFT)([^A-Za-z.]|$)', 'Ltf'),
        (r'(^|[^A-Za-z.])(RTF|TFR|RIGHT.*TOP.*FRONT|FRONT.*TOP.*RIGHT|TOP.*FRONT.*RIGHT)([^A-Za-z.]|$)', 'Rtf'),
        (r'(^|[^A-Za-z.])(LSS|SSL|LEFT.*SIDE|SIDE.*LEFT)([^A-Za-z.]|$)', 'Lss'),
        (r'(^|[^A-Za-z.])(RSS|SSR|RIGHT.*SIDE|SIDE.*RIGHT)([^A-Za-z.]|$)', 'Rss'),
        (r'(^|[^A-Za-z.])(LRS|SRL|LEFT.*REAR|REAR.*LEFT|BACK.*LEFT)([^A-Za-z.]|$)', 'Lrs'),
        (r'(^|[^A-Za-z.])(RRS|SRR|RIGHT.*REAR|REAR.*RIGHT|BACK.*RIGHT)([^A-Za-z.]|$)', 'Rrs'),
        (r'(^|[^A-Za-z.])(LS|LEFT.*SURROUND|SURROUND.*LEFT)([^A-Za-z.]|$)', 'Ls'),
        (r'(^|[^A-Za-z.])(RS|RIGHT.*SURROUND|SURROUND.*RIGHT)([^A-Za-z.]|$)', 'Rs'),
        (r'(^|[^A-Za-z.])(FC|FRONT.*CENTER|CENTER.*FRONT)([^A-Za-z.]|$)', 'C'),
        (r'(^|[^A-Za-z.])(FL|FRONT.*LEFT)([^A-Za-z.]|$)', 'L'),
        (r'(^|[^A-Za-z.])(FR|FRONT.*RIGHT)([^A-Za-z.]|$)', 'R'),
        (r'(^|[^A-Za-z.])(CENTER|CENTRE)([^A-Za-z.]|$)', 'C'),
        (r'(^|[^A-Za-z.])C([^A-Za-z.]|$)', 'C'),
        (r'(^|[^A-Za-z.])LEFT([^A-Za-z.]|$)', 'L'),
        (r'(^|[^A-Za-z.])RIGHT([^A-Za-z.]|$)', 'R'),
        (r'(^|[^A-Za-z.])L([^A-Za-z.]|$)', 'L'),
        (r'(^|[^A-Za-z.])R([^A-Za-z.]|$)', 'R'),
    ]
    for pattern, ch_id in patterns:
        if re.search(pattern, n):
            return ch_id
    return ""


def _guess_channel_by_index(file_count: int, file_index: int) -> str:
    """根据文件数量和索引推测声道标识（用于自定义模式回退）"""
    configs = {
        2: ['L', 'R'],
        6: ['L', 'R', 'C', 'LFE', 'Ls', 'Rs'],
        8: ['L', 'R', 'C', 'LFE', 'Lss', 'Rss', 'Lrs', 'Rrs'],
        10: ['L', 'R', 'C', 'LFE', 'Ls', 'Rs', 'Ltf', 'Rtf', 'Ltr', 'Rtr'],
        12: ['L', 'R', 'C', 'LFE', 'Lss', 'Rss', 'Lrs', 'Rrs', 'Ltf', 'Rtf', 'Ltb', 'Rtb'],
    }
    if file_count in configs and file_index < len(configs[file_count]):
        return configs[file_count][file_index]
    return ""


def auto_match_mono_files(
    file_paths: List[str],
    template_name: Optional[str] = None
) -> List[Tuple[str, str]]:
    """
    对单声道 WAV 文件列表进行智能声道匹配（零 GUI 依赖）。

    这是从 SmartMultiMonoDialog.auto_match() 完整提取的独立版本，
    打分逻辑与弹窗版完全一致，可用于无界面自动匹配或单元测试。

    Args:
        file_paths: 文件路径列表
        template_name: 指定模板名称，None 则根据文件数量自动选择

    Returns:
        [(文件路径, 声道标识), ...] 按模板声道顺序排列
    """
    if not file_paths:
        return []

    # 自动选择模板
    if template_name is None:
        cfg_map = {
            2: 'Stereo (2.0)',
            6: '5.1 (6ch)',
            8: '7.1 (8ch)',
            10: '5.1.4 (10ch)',
            12: '7.1.4 (12ch)',
        }
        template_name = cfg_map.get(len(file_paths), None)

    selected = [(p, "?") for p in file_paths]

    # ---------- 自定义模式 ----------
    if not template_name or template_name not in CHANNEL_TEMPLATES:
        for i, (path, _) in enumerate(selected):
            # 1. iXML
            ixml_label = _read_wav_channel_label(path)
            if ixml_label:
                selected[i] = (path, ixml_label)
                continue
            # 2. 文件名识别
            name = Path(path).stem
            ch_id = _extract_channel_id(name)
            if ch_id:
                selected[i] = (path, ch_id)
            else:
                # 3. 按数量推断
                guessed = _guess_channel_by_index(len(selected), i)
                selected[i] = (path, guessed if guessed else "?")
        return selected

    # ---------- 模板模式 ----------
    config = CHANNEL_TEMPLATES[template_name]
    channels = config["channels"]
    patterns = config["patterns"]

    # 重置
    for i, (path, _) in enumerate(selected):
        selected[i] = (path, "?")

    matched_indices = set()

    for ch_idx, (ch_name, pattern) in enumerate(zip(channels, patterns)):
        best_match = -1
        best_score = -1

        for file_idx, (path, _) in enumerate(selected):
            if file_idx in matched_indices:
                continue

            filename = Path(path).stem
            dot_parts = filename.split('.')
            after_dot = dot_parts[-1] if len(dot_parts) > 1 else ""

            score = 0
            match_pos = -1

            # 0. iXML 元数据（最高优先级，10000 分）
            ixml_label = _read_wav_channel_label(path)
            if ixml_label and ixml_label.upper() == ch_name.upper():
                score = 10000
                match_pos = 0
            # 1. _extract_channel_id（5000 分）
            else:
                extracted_id = _extract_channel_id(filename)
                if extracted_id and extracted_id.upper() == ch_name.upper():
                    score = 5000
                    match_pos = filename.rfind('.' + after_dot)
                else:
                    score = 0

            # 2. 点号后完全匹配（2000 分）
            if score == 0 and after_dot.upper() == ch_name.upper():
                score = 2000
                match_pos = filename.rfind('.' + after_dot)
            # 3. 点号后正则匹配（1500 分）
            elif score == 0 and re.search(pattern, after_dot, re.IGNORECASE):
                score = 1500
                match_pos = filename.rfind('.' + after_dot)
            # 4. 整个文件名完全匹配（1000 分）
            elif score == 0 and filename.upper() == ch_name.upper():
                score = 1000
                match_pos = 0
            # 5. 整个文件名正则匹配（500 分 + 位置）
            elif score == 0 and re.search(pattern, filename, re.IGNORECASE):
                match = re.search(pattern, filename, re.IGNORECASE)
                score = 500
                match_pos = match.start()
                score += match_pos
            # 6. 模糊匹配（100 分 + 位置）
            elif score == 0 and ch_name.upper() in filename.upper():
                score = 100
                match_pos = filename.upper().find(ch_name.upper())
                score += match_pos

            if score > best_score:
                best_score = score
                best_match = file_idx

        if best_match >= 0 and best_score > 0:
            matched_indices.add(best_match)
            selected[best_match] = (selected[best_match][0], channels[ch_idx])

    # 按声道顺序排序
    def sort_key(item):
        _, ch_name = item
        if ch_name == "?":
            return 9999
        if ch_name in channels:
            return channels.index(ch_name)
        return 9998

    selected.sort(key=sort_key)
    return selected


class SmartMultiMonoDialog(QDialog):
    """智能声道匹配对话框 - 改进版，支持点号分隔的声道标识"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("智能声道匹配")
        self.setMinimumSize(800, 550)

        self.selected_files: List[Tuple[str, str]] = []
        self.current_template = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 模板选择
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("声道模板:"))
        self.template_combo = QComboBox()
        self.template_combo.addItems(list(CHANNEL_TEMPLATES.keys()) + ["自定义"])
        self.template_combo.currentTextChanged.connect(self.on_template_changed)
        template_layout.addWidget(self.template_combo)

        self.expected_count_label = QLabel("")
        template_layout.addWidget(self.expected_count_label)
        template_layout.addStretch()
        layout.addLayout(template_layout)

        # 显示预期声道顺序
        order_layout = QHBoxLayout()
        order_layout.addWidget(QLabel("预期声道顺序:"))
        self.order_display = QLabel("-")
        self.order_display.setStyleSheet("color: #667eea; font-weight: bold;")
        order_layout.addWidget(self.order_display)
        order_layout.addStretch()
        layout.addLayout(order_layout)

        # 三栏布局
        main_layout = QHBoxLayout()

        # 左：预期声道列表
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("预期声道:"))
        self.expected_list = QListWidget()
        self.expected_list.setMaximumWidth(100)
        left_layout.addWidget(self.expected_list)

        # 中：匹配结果
        center_layout = QVBoxLayout()
        center_layout.addWidget(QLabel("匹配结果 (声道 ← 文件):"))
        self.match_list = QListWidget()
        self.match_list.setMinimumWidth(400)
        center_layout.addWidget(self.match_list)

        # 右：操作按钮
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("操作:"))
        right_layout.addSpacing(10)

        self.auto_match_btn = QPushButton("🎯 自动匹配")
        self.auto_match_btn.setToolTip("根据文件名后缀自动识别声道")
        self.auto_match_btn.clicked.connect(self.auto_match)
        right_layout.addWidget(self.auto_match_btn)

        self.add_btn = QPushButton("➕ 添加文件")
        self.add_btn.clicked.connect(self.add_files)
        right_layout.addWidget(self.add_btn)

        self.clear_btn = QPushButton("🗑 清空")
        self.clear_btn.clicked.connect(self.clear_all)
        right_layout.addWidget(self.clear_btn)

        right_layout.addStretch()

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(center_layout, 4)
        main_layout.addLayout(right_layout, 1)
        layout.addLayout(main_layout)

        # 显示选中文件路径
        layout.addWidget(QLabel("文件路径:"))
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        self.path_display.setPlaceholderText("未选择文件")
        layout.addWidget(self.path_display)

        # 状态信息
        self.status_label = QLabel("请选择模板并添加文件")
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)

        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.update_template_display()

    def on_template_changed(self, template_name):
        self.current_template = template_name if template_name in CHANNEL_TEMPLATES else None
        self.update_template_display()

    def update_template_display(self):
        self.expected_list.clear()

        if self.current_template and self.current_template in CHANNEL_TEMPLATES:
            config = CHANNEL_TEMPLATES[self.current_template]
            channels = config["channels"]
            self.order_display.setText(" → ".join(channels))
            self.expected_count_label.setText(f"({len(channels)} 声道)")

            for ch in channels:
                self.expected_list.addItem(ch)
        else:
            self.order_display.setText("自定义 (无固定顺序)")
            self.expected_count_label.setText("")

    def add_files(self):
        from PySide6.QtWidgets import QFileDialog  # lazy import to avoid circular deps
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择单声道WAV文件", "", "WAV文件 (*.wav)"
        )
        if not files:
            return

        for path in files:
            try:
                info = sf.info(path)
                if info.channels != 1:
                    QMessageBox.warning(self, "跳过", f"{Path(path).name}: 不是单声道({info.channels}ch)")
                    continue

                self.selected_files.append((path, "?"))

            except Exception as e:
                QMessageBox.warning(self, "错误", f"{Path(path).name}: {e}")

        self.update_match_display()
        self.update_path_display()

        if self.current_template:
            self.auto_match()

    def auto_match(self):
        """根据文件名后缀智能匹配 - 改进版，支持点号分隔的声道标识"""
        if not self.selected_files:
            return

        if not self.current_template or self.current_template not in CHANNEL_TEMPLATES:
            # 自定义模式：优先 iXML，回退到文件名识别，最后按数量推断
            for i, (path, _) in enumerate(self.selected_files):
                if self.selected_files[i][1] == "?":
                    # 1. 尝试读取 iXML 元数据
                    ixml_label = _read_wav_channel_label(path)
                    if ixml_label:
                        self.selected_files[i] = (path, ixml_label)
                        continue
                    # 2. 回退到文件名识别
                    name = Path(path).stem
                    ch_id = _extract_channel_id(name)
                    if ch_id:
                        self.selected_files[i] = (path, ch_id)
                    else:
                        # 3. 根据文件数量和顺序推断标准配置
                        guessed = _guess_channel_by_index(len(self.selected_files), i)
                        if guessed:
                            self.selected_files[i] = (path, guessed)
                        else:
                            self.selected_files[i] = (path, "?")
            self.update_match_display()
            return

        config = CHANNEL_TEMPLATES[self.current_template]
        channels = config["channels"]
        patterns = config["patterns"]

        # 重置所有匹配
        for i, (path, _) in enumerate(self.selected_files):
            self.selected_files[i] = (path, "?")

        matched_indices = set()

        for ch_idx, (ch_name, pattern) in enumerate(zip(channels, patterns)):
            best_match = -1
            best_score = -1

            for file_idx, (path, current_ch) in enumerate(self.selected_files):
                if file_idx in matched_indices:
                    continue

                filename = Path(path).stem

                # 提取点号后的部分（如 "2005.C" -> "C"）
                dot_parts = filename.split('.')
                after_dot = dot_parts[-1] if len(dot_parts) > 1 else ""

                score = 0
                match_pos = -1

                # 0. 优先 iXML 元数据（最高优先级，10000分）
                ixml_label = _read_wav_channel_label(path)
                if ixml_label and ixml_label.upper() == ch_name.upper():
                    score = 10000
                    match_pos = 0
                # 1. 使用 _extract_channel_id 映射（高优先级，5000分）
                else:
                    extracted_id = _extract_channel_id(filename)
                    if extracted_id and extracted_id.upper() == ch_name.upper():
                        score = 5000
                        match_pos = filename.rfind('.' + after_dot)
                    else:
                        score = 0

                # 2. 点号后完全匹配（2000分）
                if score == 0 and after_dot.upper() == ch_name.upper():
                    score = 2000
                    match_pos = filename.rfind('.' + after_dot)
                # 3. 点号后正则匹配（1500分）
                elif score == 0 and re.search(pattern, after_dot, re.IGNORECASE):
                    score = 1500
                    match_pos = filename.rfind('.' + after_dot)
                # 4. 整个文件名完全匹配（1000分）
                elif score == 0 and filename.upper() == ch_name.upper():
                    score = 1000
                    match_pos = 0
                # 5. 整个文件名正则匹配（500分+位置）
                elif score == 0 and re.search(pattern, filename, re.IGNORECASE):
                    match = re.search(pattern, filename, re.IGNORECASE)
                    score = 500
                    match_pos = match.start()
                    score += match_pos
                # 6. 模糊匹配（100分+位置）
                elif score == 0 and ch_name.upper() in filename.upper():
                    score = 100
                    match_pos = filename.upper().find(ch_name.upper())
                    score += match_pos

                if score > best_score:
                    best_score = score
                    best_match = file_idx

            if best_match >= 0 and best_score > 0:
                matched_indices.add(best_match)
                path = self.selected_files[best_match][0]
                self.selected_files[best_match] = (path, channels[ch_idx])

        self.update_match_display()

    def update_match_display(self):
        """更新匹配显示（按当前模板的预期声道顺序排列）"""
        self.match_list.clear()

        # 根据当前模板获取预期声道顺序，自定义模式使用通用 fallback
        if self.current_template and self.current_template in CHANNEL_TEMPLATES:
            ch_order = CHANNEL_TEMPLATES[self.current_template]["channels"]
        else:
            ch_order = ['L', 'R', 'C', 'LFE', 'Ls', 'Rs', 'Lss', 'Rss', 'Lrs', 'Rrs', 'Ltf', 'Rtf', 'Ltr', 'Rtr', 'Ltb', 'Rtb']

        def sort_key(item):
            _, ch_name = item
            if ch_name == "?":
                return 9999
            if ch_name in ch_order:
                return ch_order.index(ch_name)
            return 9998

        # 按声道顺序排序显示
        sorted_files = sorted(self.selected_files, key=sort_key)

        for path, ch_name in sorted_files:
            filename = Path(path).name

            if ch_name == "?":
                display = f"[未匹配]  ←  {filename}"
                self.match_list.addItem(display)
                self.match_list.item(self.match_list.count() - 1).setForeground(QColor("#e74c3c"))
            else:
                # 检测是否来自 iXML
                ixml_label = _read_wav_channel_label(path)
                source = "📋iXML" if ixml_label == ch_name else "🔤文件名"
                display = f"[{ch_name}] {source} ←  {filename}"
                self.match_list.addItem(display)
                self.match_list.item(self.match_list.count() - 1).setForeground(QColor("#27ae60"))

        # 更新状态
        total = len(self.selected_files)
        matched = sum(1 for _, ch in self.selected_files if ch != "?")

        if self.current_template:
            expected = len(CHANNEL_TEMPLATES[self.current_template]["channels"])
            if matched == expected and total == expected:
                self.status_label.setText(f"✓ 完美匹配: {matched}/{expected} 声道")
                self.status_label.setStyleSheet("color: #27ae60;")
            else:
                self.status_label.setText(f"已匹配: {matched}/{total} | 预期: {expected} 声道")
                self.status_label.setStyleSheet("color: #f39c12;" if matched < expected else "color: #27ae60;")
        else:
            self.status_label.setText(f"文件数: {total} | 自定义模式")
            self.status_label.setStyleSheet("color: #888;")

    def update_path_display(self):
        """显示选中文件路径"""
        if self.selected_files:
            first_dir = Path(self.selected_files[0][0]).parent
            self.path_display.setText(str(first_dir))
        else:
            self.path_display.setText("")

    def clear_all(self):
        self.selected_files = []
        self.match_list.clear()
        self.path_display.setText("")
        self.status_label.setText("请选择模板并添加文件")
        self.status_label.setStyleSheet("color: #888;")

    def on_ok(self):
        if not self.selected_files:
            QMessageBox.warning(self, "警告", "请至少添加一个文件")
            return

        for path, ch in self.selected_files:
            if not Path(path).exists():
                QMessageBox.critical(self, "错误", f"文件不存在:\n{path}")
                return

        unmatched = [Path(p).name for p, c in self.selected_files if c == "?"]
        if unmatched:
            reply = QMessageBox.question(
                self, "未匹配声道",
                f"以下文件未匹配:\n" + "\n".join(unmatched[:5]) + f"\n\n是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        self.accept()

    def get_files(self) -> List[Tuple[str, str]]:
        """获取按声道顺序排序后的文件列表"""
        sorted_files = sorted(self.selected_files, key=lambda x: x[1])
        return [(p, c) for p, c in sorted_files if c != "?"]
