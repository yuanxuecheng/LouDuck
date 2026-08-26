"""
ADM (Audio Definition Model) 解析器
支持 ITU-R BS.2076 和 BW64 文件格式
修复：
- 动态命名空间检测（支持多种ADM标准）
- 基于规则的声道名称智能识别（支持长描述性名称如RoomCentric）
- 完整的7.1.4扬声器标签映射
- 增强的错误处理和调试输出
- 支持 typeDefinition 和 typeLabel 两种属性
"""

import re
import struct
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
import numpy as np

try:
    from PySide6.QtCore import QCoreApplication
except ImportError:
    QCoreApplication = None


def _tr(context: str, text: str) -> str:
    """翻译包装器，无 Qt 时回退原文"""
    if QCoreApplication is not None:
        return QCoreApplication.translate(context, text)
    return text


@dataclass
class ADMTrack:
    """ADM 音轨信息"""
    index: int
    uid: str
    format_id: str
    pack_id: str


@dataclass
class ADMChannel:
    """ADM 声道信息"""
    id: str
    name: str
    type: str  # DirectSpeakers, Objects, HOA, etc.
    position: Optional[Dict] = None
    speaker_label: Optional[str] = None
    is_lfe: bool = False


# ============ 配置识别规则引擎 ============

# 各配置的空间特征规则
CONFIG_RULES = {
    'stereo': {
        'required': ['front_left', 'front_right'],
        'forbidden': ['surround', 'rear', 'top', 'height', 'lfe'],
        'max_channels': 2,
        'description': '立体声'
    },
    '5.1': {
        'required': ['front_left', 'front_right', 'front_center', 'lfe', 'surround_left', 'surround_right'],
        'forbidden': ['top', 'height', 'rear', 'side'],
        'max_channels': 6,
        'description': '5.1 环绕声'
    },
    '7.1': {
        'required': ['front_left', 'front_right', 'front_center', 'lfe', 'side_left', 'side_right', 'rear_left', 'rear_right'],
        'forbidden': ['top', 'height'],
        'max_channels': 8,
        'description': '7.1 环绕声'
    },
    '5.1.4': {
        'required': ['front_left', 'front_right', 'front_center', 'lfe', 'surround_left', 'surround_right', 
                     'top_front_left', 'top_front_right', 'top_rear_left', 'top_rear_right'],
        'forbidden': ['side', 'rear_bottom'],
        'max_channels': 10,
        'description': '5.1.4 沉浸式'
    },
    '7.1.4': {
        'required': ['front_left', 'front_right', 'front_center', 'lfe', 'side_left', 'side_right', 
                     'rear_left', 'rear_right', 'top_front_left', 'top_front_right', 'top_rear_left', 'top_rear_right'],
        'forbidden': [],
        'max_channels': 12,
        'description': '7.1.4 沉浸式'
    },
    '7.1.2': {
        'required': ['front_left', 'front_right', 'front_center', 'lfe', 'side_left', 'side_right', 
                     'rear_left', 'rear_right', 'top_front_left', 'top_front_right'],
        'forbidden': ['top_rear_left', 'top_rear_right'],
        'max_channels': 10,
        'description': '7.1.2 沉浸式'
    }
}


def normalize_channel_name(name: str) -> Optional[str]:
    """
    将任意声道名称标准化为空间特征词
    支持：英文缩写、数字编码、ITU标签、带点号后缀、长描述性名称等
    """
    if not name:
        return None
    
    # 清理
    n = name.upper().strip()
    
    # 提取点号后缀（如 "2005.L" → "L"）
    if '.' in n:
        parts = n.split('.')
        suffix = parts[-1]
        if len(suffix) <= 8:
            n = suffix
    
    # ==== 第一步：检测LFE（最明确）====
    if 'LFE' in n and 'LEFT' not in n:
        return 'lfe'
    
    # ==== 第二步：检测顶部声道（有TOP/UP/HEIGHT）====
    if 'TOP' in n or 'UP' in n or 'HEIGHT' in n or 'ELEVATED' in n or 'OVERHEAD' in n:
        # 顶部 + 前后判断
        if 'FRONT' in n or 'FWD' in n or 'FORWARD' in n:
            if 'LEFT' in n or n.endswith(' L') or ' L ' in n:
                return 'top_front_left'
            elif 'RIGHT' in n or n.endswith(' R') or ' R ' in n:
                return 'top_front_right'
        elif 'REAR' in n or 'BACK' in n or 'REARWARD' in n:
            if 'LEFT' in n or n.endswith(' L') or ' L ' in n:
                return 'top_rear_left'
            elif 'RIGHT' in n or n.endswith(' R') or ' R ' in n:
                return 'top_rear_right'
        elif 'CENTER' in n or 'CENTRE' in n or 'MID' in n or 'MIDDLE' in n:
            return 'top_front_center'
        else:
            # 只有TOP + LEFT/RIGHT，无前后 → 默认前（7.1.2特征）
            if 'LEFT' in n or n.endswith(' L') or ' L ' in n:
                return 'top_front_left'
            elif 'RIGHT' in n or n.endswith(' R') or ' R ' in n:
                return 'top_front_right'
    
    # ==== 第三步：检测底层声道 ====
    
    # 判断位置特征（优先级：REAR > SIDE > SURROUND > FRONT）
    has_rear = 'REAR' in n or 'BACK' in n
    has_side = 'SIDE' in n
    has_surround = 'SURROUND' in n
    has_front = not has_rear and not has_side and not has_surround
    
    # 判断左右
    has_left = 'LEFT' in n or n.endswith(' L') or ' L ' in n
    has_right = 'RIGHT' in n or n.endswith(' R') or ' R ' in n
    has_center = 'CENTER' in n or 'CENTRE' in n or 'MID' in n or 'MIDDLE' in n
    
    # 组合判断
    if has_front:
        if has_left and not has_right:
            return 'front_left'
        elif has_right and not has_left:
            return 'front_right'
        elif has_center:
            return 'front_center'
    
    if has_side and not has_rear:
        if has_left and not has_right:
            return 'side_left'
        elif has_right and not has_left:
            return 'side_right'
    
    if has_rear:
        if has_left and not has_right:
            return 'rear_left'
        elif has_right and not has_left:
            return 'rear_right'
    
    if has_surround and not has_side and not has_rear:
        if has_left and not has_right:
            return 'surround_left'
        elif has_right and not has_left:
            return 'surround_right'
    
    # ==== 第四步：简化名称匹配（短名称/缩写）====
    # 去除常见前缀后缀
    n_clean = n
    for prefix in ['ROOMCENTRIC', 'ROOM', 'CENTRIC', 'CHANNEL', 'CH', 'TRACK', 'TRK', 'SPEAKER', 'SPK']:
        n_clean = n_clean.replace(prefix, '')
    n_clean = n_clean.strip()
    
    # 单字母/双字母匹配
    if n_clean == 'L' or n_clean == 'FL' or n_clean == 'LF':
        return 'front_left'
    if n_clean == 'R' or n_clean == 'FR' or n_clean == 'RF':
        return 'front_right'
    if n_clean == 'C' or n_clean == 'FC':
        return 'front_center'
    if n_clean == 'LS' or n_clean == 'SL':
        return 'surround_left'
    if n_clean == 'RS' or n_clean == 'SR':
        return 'surround_right'
    if n_clean == 'LSS' or n_clean == 'SSL':
        return 'side_left'
    if n_clean == 'RSS' or n_clean == 'SSR':
        return 'side_right'
    if n_clean == 'LRS' or n_clean == 'SRL':
        return 'rear_left'
    if n_clean == 'RRS' or n_clean == 'SRR':
        return 'rear_right'
    if n_clean == 'LTF' or n_clean == 'TFL':
        return 'top_front_left'
    if n_clean == 'RTF' or n_clean == 'TFR':
        return 'top_front_right'
    if n_clean == 'LTR' or n_clean == 'TRL':
        return 'top_rear_left'
    if n_clean == 'RTR' or n_clean == 'TRR':
        return 'top_rear_right'
    if n_clean == 'LTM' or n_clean == 'TML':
        return 'top_front_left'
    if n_clean == 'RTM' or n_clean == 'TMR':
        return 'top_front_right'
    if n_clean == 'TC' or n_clean == 'TM' or n_clean == 'TMC':
        return 'top_front_center'
    
    # ==== 第五步：ITU标签匹配 ====
    if 'M+030' in n or 'M+03' in n:
        return 'front_left'
    if 'M-030' in n or 'M-03' in n:
        return 'front_right'
    if 'M+000' in n or 'M+00' in n:
        return 'front_center'
    if 'M+090' in n or 'M+09' in n:
        return 'side_left'
    if 'M-090' in n or 'M-09' in n:
        return 'side_right'
    if 'M+110' in n or 'M+11' in n:
        return 'surround_left'
    if 'M-110' in n or 'M-11' in n:
        return 'surround_right'
    if 'M+135' in n or 'M+13' in n:
        return 'rear_left'
    if 'M-135' in n or 'M-13' in n:
        return 'rear_right'
    if 'U+045' in n or 'U+04' in n:
        return 'top_front_left'
    if 'U-045' in n or 'U-04' in n:
        return 'top_front_right'
    if 'U+135' in n or 'U+13' in n:
        return 'top_rear_left'
    if 'U-135' in n or 'U-13' in n:
        return 'top_rear_right'
    if 'U+000' in n or 'U+00' in n or 'T+000' in n or 'T+00' in n:
        return 'top_front_center'
    if 'U+180' in n or 'U+18' in n:
        return 'top_rear_center'
    
    return None


def detect_config_by_features(channels: List[ADMChannel]) -> Tuple[str, float, str]:
    """
    基于空间特征识别配置
    返回: (配置名称, 置信度0-1, 描述)
    """
    # 收集所有通道的空间特征
    features: Set[str] = set()
    
    for ch in channels:
        # 优先使用名称/标签识别
        feature = normalize_channel_name(ch.name) or normalize_channel_name(ch.speaker_label)
        
        # 如果名称识别失败，尝试使用位置信息
        if not feature and ch.position:
            az = ch.position.get('azimuth', 0)
            el = ch.position.get('elevation', 0)
            feature = _position_to_feature(az, el)
        
        if feature:
            features.add(feature)
    
    # 计算各配置的匹配度
    best_config = 'unknown'
    best_score = -999
    best_confidence = 0.0
    
    for config_name, rules in CONFIG_RULES.items():
        required = set(rules['required'])
        forbidden = set(rules['forbidden'])
        
        matched_required = len(features & required)
        missing_required = len(required - features)
        violated_forbidden = len(features & forbidden)
        
        if violated_forbidden > 0:
            continue
        
        score = matched_required * 2 - missing_required
        
        ch_count = len(channels)
        if ch_count > rules['max_channels']:
            score -= (ch_count - rules['max_channels']) * 3
        
        confidence = matched_required / len(required) if len(required) > 0 else 0.0
        
        if score > best_score:
            best_score = score
            best_config = config_name
            best_confidence = confidence
    
    description = CONFIG_RULES.get(best_config, {}).get('description', '未知')
    return best_config, best_confidence, description


def _position_to_feature(azimuth: float, elevation: float) -> Optional[str]:
    """将方位角/仰角转换为空间特征词"""
    az = round(azimuth)
    el = round(elevation)
    
    if el < -20:
        return 'lfe'
    
    if el > 30:
        if abs(az) <= 45:
            return 'top_front_center'
        elif az > 0 and az <= 90:
            return 'top_front_left'
        elif az < 0 and az >= -90:
            return 'top_front_right'
        elif az > 90 and az <= 180:
            return 'top_rear_left'
        elif az < -90 and az >= -180:
            return 'top_rear_right'
    
    if el <= 30:
        if abs(az) <= 15:
            return 'front_center'
        elif az > 15 and az <= 60:
            return 'front_left'
        elif az < -15 and az >= -60:
            return 'front_right'
        elif abs(az) >= 75 and abs(az) <= 105:
            return 'side_left' if az > 0 else 'side_right'
        elif abs(az) >= 120:
            return 'surround_left' if az > 0 else 'surround_right'
    
    return None


# ============ ADM 核心类 ============

class ADM:
    """ADM 元数据模型 (ITU-R BS.2076)"""
    
    def __init__(self, axml_data: bytes, chna_data: Optional[bytes] = None):
        self.axml_data = axml_data
        self.chna_data = chna_data
        
        self.programmes: List[Dict] = []
        self.contents: List[Dict] = []
        self.objects: List[Dict] = []
        self.channel_formats: List[ADMChannel] = []
        self.track_mappings: List[ADMTrack] = []
        
        # 渲染器与创作软件信息 (ITU-R BS.2076-3 §5.8.6)
        self.renderer_info: Optional[Dict] = None
        self.authoring_info: Optional[Dict] = None
        
        self.ns = {}
        self.ns_uri = None
        
    def _detect_namespace(self, root):
        """动态检测XML命名空间"""
        root_tag = root.tag
        if root_tag.startswith('{'):
            ns_uri = root_tag.split('}')[0][1:]
            self.ns_uri = ns_uri
            self.ns = {'adm': ns_uri}
            print(f"[ADM解析] 检测到命名空间: {ns_uri}")
        else:
            self.ns = {'adm': ''}
            print("[ADM解析] 无命名空间或空命名空间")
    
    def _findall(self, element, path):
        """安全的查找方法"""
        if self.ns_uri:
            return element.findall(path, self.ns)
        else:
            local_path = path.replace('adm:', '')
            return element.findall(local_path)
    
    def _find(self, element, path):
        """安全的单个查找方法"""
        if self.ns_uri:
            return element.find(path, self.ns)
        else:
            local_path = path.replace('adm:', '')
            return element.find(local_path)
    
    def parse(self):
        """解析 ADM XML"""
        try:
            root = ET.fromstring(self.axml_data.decode('utf-8'))
            self._detect_namespace(root)
            
            print(f"[ADM解析] 根元素: {root.tag}")
            
            # 解析 audioProgramme
            programmes = self._findall(root, './/adm:audioProgramme')
            print(f"[ADM解析] 找到 {len(programmes)} 个 audioProgramme")
            for prog in programmes:
                prog_data = {
                    'id': prog.get('audioProgrammeID'),
                    'name': prog.get('audioProgrammeName'),
                    'content_refs': [ref.text for ref in self._findall(prog, 'adm:audioContentIDRef') if ref.text]
                }
                self.programmes.append(prog_data)
            
            # 解析 audioContent
            contents = self._findall(root, './/adm:audioContent')
            print(f"[ADM解析] 找到 {len(contents)} 个 audioContent")
            for content in contents:
                content_data = {
                    'id': content.get('audioContentID'),
                    'name': content.get('audioContentName'),
                    'object_refs': [ref.text for ref in self._findall(content, 'adm:audioObjectIDRef') if ref.text],
                    'dialogue': content.get('dialogue')
                }
                self.contents.append(content_data)
            
            # 解析 audioObject
            objects = self._findall(root, './/adm:audioObject')
            print(f"[ADM解析] 找到 {len(objects)} 个 audioObject")
            for obj in objects:
                obj_data = {
                    'id': obj.get('audioObjectID'),
                    'name': obj.get('audioObjectName'),
                    'gain': float(obj.get('gain', '1.0')),
                    'mute': obj.get('mute', '0') == '1',
                    'track_refs': [ref.text for ref in self._findall(obj, 'adm:audioTrackUIDRef') if ref.text],
                    'pack_refs': [ref.text for ref in self._findall(obj, 'adm:audioPackFormatIDRef') if ref.text]
                }
                self.objects.append(obj_data)
            
            # 解析 authoringInformation (ITU-R BS.2076-3 §5.8.6)
            authoring_elements = self._findall(root, './/adm:authoringInformation')
            if authoring_elements:
                auth = authoring_elements[0]
                self.authoring_info = {
                    'reference_layouts': [],
                    'renderers': []
                }
                
                # 解析 referenceLayout
                ref_layouts = self._findall(auth, 'adm:referenceLayout')
                for rl in ref_layouts:
                    pack_ref = self._find(rl, 'adm:audioPackFormatIDRef')
                    if pack_ref is not None and pack_ref.text:
                        self.authoring_info['reference_layouts'].append(pack_ref.text)
                
                # 解析 renderer (ITU-R BS.2076-3 Table A1-52/A1-53)
                renderers = self._findall(auth, 'adm:renderer')
                for renderer in renderers:
                    renderer_data = {
                        'uri': renderer.get('uri', ''),
                        'name': renderer.get('name', ''),
                        'version': renderer.get('version', ''),
                        'coordinate_mode': renderer.get('coordinateMode', ''),
                        'pack_format_refs': [ref.text for ref in self._findall(renderer, 'adm:audioPackFormatIDRef') if ref.text],
                        'object_refs': [ref.text for ref in self._findall(renderer, 'adm:audioObjectIDRef') if ref.text]
                    }
                    self.authoring_info['renderers'].append(renderer_data)
                
                # 兼容：如果只有一个renderer，也设置到renderer_info
                if self.authoring_info['renderers']:
                    self.renderer_info = self.authoring_info['renderers'][0]
                    print(f"[ADM解析] 检测到渲染器: {self.renderer_info.get('name', 'N/A')} v{self.renderer_info.get('version', 'N/A')}")
                
                print(f"[ADM解析] 创作信息: {len(self.authoring_info['reference_layouts'])}个参考布局, {len(self.authoring_info['renderers'])}个渲染器")
            
            # === 新增：全局搜索 renderer（部分ADM的renderer不在authoringInformation内）===
            if not self.renderer_info:
                all_renderers = self._findall(root, './/adm:renderer')
                if all_renderers:
                    for renderer in all_renderers:
                        renderer_data = {
                            'uri': renderer.get('uri', ''),
                            'name': renderer.get('name', ''),
                            'version': renderer.get('version', ''),
                            'coordinate_mode': renderer.get('coordinateMode', ''),
                            'pack_format_refs': [ref.text for ref in self._findall(renderer, 'adm:audioPackFormatIDRef') if ref.text],
                            'object_refs': [ref.text for ref in self._findall(renderer, 'adm:audioObjectIDRef') if ref.text]
                        }
                        if not self.authoring_info:
                            self.authoring_info = {'reference_layouts': [], 'renderers': []}
                        self.authoring_info['renderers'].append(renderer_data)
                    self.renderer_info = self.authoring_info['renderers'][0]
                    print(f"[ADM解析] 从全局搜索找到渲染器: {self.renderer_info.get('name', 'N/A')}")
            
            # === 新增：从 audioProgramme 属性查找 authoringTool / renderer ===
            if not self.renderer_info:
                for prog in programmes:
                    tool = prog.get('authoringTool', '') or prog.get('renderer', '')
                    if tool:
                        renderer_data = {
                            'uri': '',
                            'name': tool,
                            'version': prog.get('authoringToolVersion', ''),
                            'coordinate_mode': '',
                            '_source': 'audioProgramme属性'
                        }
                        if not self.authoring_info:
                            self.authoring_info = {'reference_layouts': [], 'renderers': []}
                        self.authoring_info['renderers'].append(renderer_data)
                        self.renderer_info = renderer_data
                        print(f"[ADM解析] 从audioProgramme属性找到渲染器: {tool}")
                        break
            
            # === 新增：从内容推断（Dolby Atmos特征）===
            if not self.renderer_info:
                # 特征1：节目名含 Atmos / Dolby
                inferred_name = None
                for prog in self.programmes:
                    prog_name = (prog.get('name', '') or '').lower()
                    if 'atmos' in prog_name or 'dolby' in prog_name:
                        inferred_name = 'Dolby Atmos Renderer'
                        break
                
                # 特征2：声道使用 RoomCentric 命名法
                if not inferred_name:
                    for ch in self.channel_formats:
                        if 'roomcentric' in (ch.name or '').lower():
                            inferred_name = 'Dolby Atmos Renderer (Room-Centric)'
                            break
                
                if inferred_name:
                    renderer_data = {
                        'uri': 'urn:dolby:atmos',
                        'name': inferred_name,
                        'version': '',
                        'coordinate_mode': 'room-centric',
                        '_inferred': True,
                        '_source': '内容推断（节目名/声道特征）'
                    }
                    if not self.authoring_info:
                        self.authoring_info = {'reference_layouts': [], 'renderers': []}
                    self.authoring_info['renderers'].append(renderer_data)
                    self.renderer_info = renderer_data
                    print(f"[ADM解析] 从内容推断渲染器: {inferred_name}")
            
            # 解析 audioChannelFormat
            channel_formats = self._findall(root, './/adm:audioChannelFormat')
            print(f"[ADM解析] 找到 {len(channel_formats)} 个 audioChannelFormat")
            for ch_fmt in channel_formats:
                ch_id = ch_fmt.get('audioChannelFormatID', '')
                ch_name = ch_fmt.get('audioChannelFormatName', '')
                
                ch_type = ch_fmt.get('typeDefinition', '') or ch_fmt.get('typeLabel', 'DirectSpeakers')
                # 如果 typeLabel 是数字代码，映射为类型名称
                TYPE_LABEL_MAP = {
                    '0001': 'DirectSpeakers',
                    '0002': 'Matrix',
                    '0003': 'Objects',
                    '0004': 'HOA',
                    '0005': 'Binaural',
                }
                if ch_type in TYPE_LABEL_MAP:
                    ch_type = TYPE_LABEL_MAP[ch_type]
                
                position = None
                speaker_label = None
                
                speaker = self._find(ch_fmt, './/adm:speakerLabel')
                if speaker is not None and speaker.text:
                    speaker_label = speaker.text
                else:
                    speaker = self._find(ch_fmt, 'adm:speakerLabel')
                    if speaker is not None and speaker.text:
                        speaker_label = speaker.text
                
                pos_blocks = self._findall(ch_fmt, './/adm:audioBlockFormat')
                if pos_blocks:
                    pos_block = pos_blocks[0]
                    position = {
                        'azimuth': float(pos_block.get('azimuth', 0) or 0),
                        'elevation': float(pos_block.get('elevation', 0) or 0),
                        'distance': float(pos_block.get('distance', 1.0) or 1.0)
                    }
                    # 支持笛卡尔坐标子元素格式 <position coordinate="X/Y/Z">
                    cartesian_positions = {}
                    for pos_el in self._findall(pos_block, 'adm:position'):
                        coord = pos_el.get('coordinate', '')
                        if coord and pos_el.text:
                            try:
                                cartesian_positions[coord.upper()] = float(pos_el.text)
                            except ValueError:
                                pass
                    if cartesian_positions:
                        position['cartesian'] = cartesian_positions
                        # 检测 cartesian 标志
                        cart_el = self._find(pos_block, 'adm:cartesian')
                        if cart_el is not None and cart_el.text:
                            position['is_cartesian'] = cart_el.text.strip() in ('1', 'true', 'True')
                    # 支持 <speakerLabel> 在 audioBlockFormat 内（RoomCentric 风格）
                    spk_in_block = self._find(pos_block, 'adm:speakerLabel')
                    if spk_in_block is not None and spk_in_block.text:
                        speaker_label = spk_in_block.text
                
                is_lfe = False
                if speaker_label and 'LFE' in speaker_label.upper():
                    is_lfe = True
                elif ch_name and 'LFE' in ch_name.upper():
                    is_lfe = True
                elif ch_id and 'LFE' in ch_id.upper():
                    is_lfe = True
                
                self.channel_formats.append(ADMChannel(
                    id=ch_id,
                    name=ch_name,
                    type=ch_type,
                    position=position,
                    speaker_label=speaker_label,
                    is_lfe=is_lfe
                ))
            
            if self.chna_data:
                self._parse_chna()
            
            print(f"[ADM解析] 完成: {len(self.programmes)} programmes, {len(self.contents)} contents, "
                  f"{len(self.objects)} objects, {len(self.channel_formats)} channels")
            
        except Exception as e:
            print(f"[ADM解析错误] {e}")
            import traceback
            traceback.print_exc()
    
    def _parse_chna(self):
        """解析 chna chunk"""
        if not self.chna_data or len(self.chna_data) < 4:
            return
        
        num_tracks = struct.unpack('<H', self.chna_data[0:2])[0]
        
        offset = 4
        for i in range(min(num_tracks, 100)):
            if offset + 12 > len(self.chna_data):
                break
            
            track_id = struct.unpack('<H', self.chna_data[offset:offset+2])[0]
            
            try:
                uid_bytes = self.chna_data[offset+2:offset+14]
                uid = uid_bytes.decode('ascii', errors='ignore').strip('\x00')
            except:
                uid = f"track_{i}"
            
            self.track_mappings.append(ADMTrack(
                index=i,
                uid=uid,
                format_id='',
                pack_id=''
            ))
            offset += 12
    
    def get_channel_config(self) -> List[ADMChannel]:
        """获取声床配置"""
        if self.channel_formats:
            return [ch for ch in self.channel_formats if ch.type == 'DirectSpeakers']
        return []
    
    def detect_configuration(self) -> Tuple[str, float, str]:
        """
        自动识别声床配置
        返回: (配置名称, 置信度, 描述)
        """
        direct_speakers = self.get_channel_config()
        if not direct_speakers:
            return 'unknown', 0.0, _tr('ADM', '未找到声床')
        
        return detect_config_by_features(direct_speakers)
    
    def to_itu1770_config(self, num_channels: Optional[int] = None):
        """转换为 ITU1770Meter 的 ChannelConfig
        
        Args:
            num_channels: BW64 文件实际音频通道数。若提供，会补齐缺失通道配置，
                         避免 DirectSpeakers 数量与实际通道数不一致导致越界。
        """
        from itu1770_meter import ChannelConfig
        
        adm_channels = self.get_channel_config()
        result = []
        
        print(f"[ADM转换] 转换 {len(adm_channels)} 个DirectSpeakers声道")
        
        for ch in adm_channels:
            azimuth = 0
            elevation = 0
            
            # 优先使用speaker_label映射（即使position存在但为0）
            if ch.speaker_label:
                az, el = self._speaker_label_to_angles(ch.speaker_label)
                if az != 0 or el != 0:
                    azimuth, elevation = az, el
                elif ch.position and (ch.position.get('azimuth', 0) != 0 or ch.position.get('elevation', 0) != 0):
                    azimuth = ch.position.get('azimuth', 0)
                    elevation = ch.position.get('elevation', 0)
            elif ch.position:
                azimuth = ch.position.get('azimuth', 0)
                elevation = ch.position.get('elevation', 0)
            
            print(f"  {ch.name}: az={azimuth}, el={elevation}, LFE={ch.is_lfe}")
            
            result.append(ChannelConfig(
                name=ch.name or ch.id,
                azimuth=azimuth,
                elevation=elevation,
                is_lfe=ch.is_lfe
            ))
        
        # 补齐缺失通道（Objects / HOA 等），确保配置长度与实际音频通道数一致
        if num_channels is not None:
            direct_count = len(result)
            if direct_count < num_channels:
                print(f"[ADM转换] 补齐 {num_channels - direct_count} 个非DirectSpeakers通道")
                for i in range(direct_count, num_channels):
                    result.append(ChannelConfig(
                        name=f"Ch{i + 1}",
                        azimuth=0.0,
                        elevation=0.0,
                        is_lfe=False
                    ))
            elif direct_count > num_channels:
                print(f"[ADM转换] 警告: DirectSpeakers数量({direct_count})超过音频通道数({num_channels})，已截断")
                result = result[:num_channels]
        
        return result
    
    def get_renderer_summary(self) -> str:
        """获取渲染器信息摘要"""
        if not self.renderer_info:
            return _tr('ADM', "未检测到渲染器信息")
        
        parts = []
        info = self.renderer_info
        if info.get('name'):
            parts.append(_tr('ADM', "名称: {name}").format(name=info['name']))
        if info.get('version'):
            parts.append(_tr('ADM', "版本: {version}").format(version=info['version']))
        if info.get('uri'):
            parts.append(f"URI: {info['uri']}")
        if info.get('coordinate_mode'):
            parts.append(_tr('ADM', "坐标模式: {mode}").format(mode=info['coordinate_mode']))
        if info.get('_inferred'):
            parts.append(_tr('ADM', "(基于内容推断)"))
        elif info.get('_source'):
            parts.append(f"({info['_source']})")
        
        return " | ".join(parts) if parts else _tr('ADM', "渲染器信息不完整")
    
    def get_authoring_summary(self) -> str:
        """获取创作软件信息摘要"""
        if not self.authoring_info:
            return _tr('ADM', "未检测到创作软件信息")
        
        parts = []
        info = self.authoring_info
        if info.get('reference_layouts'):
            parts.append(_tr('ADM', "参考布局: {layouts}").format(layouts=', '.join(info['reference_layouts'])))
        if info.get('renderers'):
            for r in info['renderers']:
                name = r.get('name', _tr('ADM', '未知'))
                if r.get('_inferred'):
                    parts.append(_tr('ADM', "渲染器: {name} (推断)").format(name=name))
                else:
                    parts.append(_tr('ADM', "渲染器: {name}").format(name=name))
        
        return " | ".join(parts) if parts else _tr('ADM', "创作信息不完整")
    
    def _speaker_label_to_angles(self, label: str):
        """将扬声器标签转换为角度"""
        if not label:
            return (0, 0)
        
        mapping = {
            'M+030': (30, 0), 'M-030': (-30, 0),
            'M+000': (0, 0),
            'M+110': (110, 0), 'M-110': (-110, 0),
            'M+090': (90, 0), 'M-090': (-90, 0),
            'M+135': (135, 0), 'M-135': (-135, 0),
            'M+045': (45, 0), 'M-045': (-45, 0),
            'U+030': (30, 45), 'U-030': (-30, 45),
            'U+110': (110, 45), 'U-110': (-110, 45),
            'U+090': (90, 45), 'U-090': (-90, 45),
            'U+135': (135, 45), 'U-135': (-135, 45),
            'U+045': (45, 45), 'U-045': (-45, 45),
            'U+180': (180, 45),
            'U+000': (0, 45),
            'T+000': (0, 90),
            'B+000': (0, -30),
            'LFE1': (0, 0), 'LFE2': (0, 0),
            'L': (30, 0), 'R': (-30, 0),
            'C': (0, 0), 'Centre': (0, 0), 'Center': (0, 0),
            'LFE': (0, 0),
            'Ls': (110, 0), 'Rs': (-110, 0),
            'Lss': (90, 0), 'Rss': (-90, 0),
            'Lrs': (135, 0), 'Rrs': (-135, 0),
            'Ltf': (45, 45), 'Rtf': (-45, 45),
            'Ltb': (135, 45), 'Rtb': (-135, 45),
            'Ltr': (135, 45), 'Rtr': (-135, 45),
        }
        return mapping.get(label, (0, 0))


class BW64Parser:
    """BW64 文件解析器 (ITU-R BS.2088)"""
    
    CHUNK_ID_AXML = b'axml'
    CHUNK_ID_CHNA = b'chna'
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.axml_data: Optional[bytes] = None
        self.chna_data: Optional[bytes] = None
        self.audio_info: Optional[Dict] = None
        self.adm: Optional[ADM] = None
        self.audio_offset: int = 0
        self.audio_size: int = 0
        self.ds64_info: Optional[Dict[str, int]] = None
    
    def _read_ds64(self, f) -> Optional[Dict[str, int]]:
        """读取 ds64 chunk 中的 64 位大小信息。
        
        BW64/RF64 大文件（>4GB）会在 32 位 file_size 字段使用 0xFFFFFFFF，
        并在 ds64 chunk 中提供真正的 64 位文件大小与 data chunk 大小。
        返回 {'riff_size': int, 'data_size': int, 'sample_count': int}，
        如果没有 ds64 则返回 None。
        """
        start_pos = f.tell()
        try:
            while True:
                chunk_id = f.read(4)
                if len(chunk_id) < 4:
                    break
                chunk_size_bytes = f.read(4)
                if len(chunk_size_bytes) < 4:
                    break
                chunk_size = struct.unpack('<I', chunk_size_bytes)[0]
                
                if chunk_id == b'ds64':
                    # ds64 chunk layout:
                    #   riffSize: uint64
                    #   dataSize: uint64
                    #   sampleCount: uint64
                    #   tableLength: uint32
                    #   table entries...
                    riff_size = struct.unpack('<Q', f.read(8))[0]
                    data_size = struct.unpack('<Q', f.read(8))[0]
                    sample_count = struct.unpack('<Q', f.read(8))[0]
                    print(f"[BW64解析] 检测到 ds64 chunk，riffSize={riff_size}, dataSize={data_size}, sampleCount={sample_count}")
                    return {
                        'riff_size': riff_size,
                        'data_size': data_size,
                        'sample_count': sample_count
                    }
                
                # 跳过当前 chunk（包括可能的填充字节）
                f.seek(chunk_size + (chunk_size % 2), 1)
        except Exception as e:
            print(f"[BW64解析] 扫描 ds64 时出错: {e}")
        finally:
            f.seek(start_pos)
        return None
    
    def _read_ds64_size(self, f) -> Optional[int]:
        """读取 ds64 chunk 中的 64 位 riffSize（兼容接口）。
        
        内部调用 _read_ds64 获取完整 ds64 信息，仅返回 riffSize。
        """
        ds64_info = self._read_ds64(f)
        return ds64_info['riff_size'] if ds64_info else None

    def parse(self) -> ADM:
        """解析 BW64/RF64 文件"""
        actual_size = self.file_path.stat().st_size
        truncated = False
        truncated_missing = 0

        with open(self.file_path, 'rb') as f:
            riff_id = f.read(4)
            if riff_id not in (b'RIFF', b'BW64', b'RF64'):
                raise ValueError(f"不是有效的 RIFF/BW64/RF64 文件: {riff_id}")
            
            file_size = struct.unpack('<I', f.read(4))[0]
            wave_id = f.read(4)
            
            if wave_id not in (b'WAVE', b'BW64'):
                raise ValueError(f"不是有效的 WAVE/BW64 格式: {wave_id}")
            
            # 大文件支持：BW64/RF64 的 32 位 file_size 通常为 0xFFFFFFFF，
            # 需要从 ds64 chunk 读取 64 位真实文件大小与 data chunk 大小。
            if riff_id in (b'BW64', b'RF64') or file_size == 0xFFFFFFFF:
                self.ds64_info = self._read_ds64(f)
                if self.ds64_info is not None:
                    file_size = self.ds64_info['riff_size']
            
            print(f"[BW64解析] 文件大小: {file_size} bytes ({file_size / (1024**3):.2f} GB), 实际大小: {actual_size} bytes ({actual_size / (1024**3):.2f} GB)")
            
            if file_size > 0 and 8 + file_size > actual_size:
                truncated = True
                truncated_missing = (8 + file_size) - actual_size
                print(f"[BW64解析] 警告: 声明文件大小大于实际文件大小 {truncated_missing} bytes，文件可能被截断")
            
            # 使用实际文件大小作为扫描上限，避免在截断文件上越界
            scan_end = min(8 + file_size, actual_size) if file_size > 0 else actual_size
            
            while f.tell() < scan_end:
                chunk_id = f.read(4)
                if len(chunk_id) < 4:
                    break
                
                try:
                    chunk_size_bytes = f.read(4)
                    if len(chunk_size_bytes) < 4:
                        break
                    chunk_size = struct.unpack('<I', chunk_size_bytes)[0]
                except Exception:
                    break
                
                remaining = actual_size - f.tell()
                
                # 防止被截断文件中的超大 chunk_size 导致越界
                if chunk_size > remaining:
                    print(f"[BW64解析] 警告: chunk {chunk_id!r} 声明大小 {chunk_size} 超过剩余字节 {remaining}，文件可能截断")
                    truncated = True
                    break
                
                if chunk_id == self.CHUNK_ID_AXML:
                    print(f"[BW64解析] 读取 axml chunk，大小: {chunk_size} bytes")
                    self.axml_data = f.read(chunk_size)
                    if chunk_size % 2:
                        f.read(1)
                
                elif chunk_id == self.CHUNK_ID_CHNA:
                    print(f"[BW64解析] 读取 chna chunk，大小: {chunk_size} bytes")
                    self.chna_data = f.read(chunk_size)
                    if chunk_size % 2:
                        f.read(1)
                
                elif chunk_id == b'fmt ':
                    fmt_data = f.read(chunk_size)
                    self.audio_info = self._parse_fmt_chunk(fmt_data)
                    if chunk_size % 2:
                        f.read(1)
                
                elif chunk_id == b'data':
                    self.audio_offset = f.tell()
                    # RF64/BW64 大文件的 data chunk 大小可能为 0xFFFFFFFF，
                    # 真实大小在 ds64 的 data_size 中。使用 data_size 跳过数据块，
                    # 而不是跳到文件末尾，因为 axml/chna 等元数据可能在 data 之后。
                    if chunk_size == 0xFFFFFFFF and self.ds64_info is not None:
                        actual_data_size = self.ds64_info['data_size']
                        print(f"[BW64解析] 64 位 data chunk，使用 ds64 dataSize: {actual_data_size} bytes")
                    else:
                        actual_data_size = chunk_size
                    self.audio_size = actual_data_size
                    # 跳过数据块；截断保护
                    skip_size = min(actual_data_size, remaining)
                    if skip_size < actual_data_size:
                        print(f"[BW64解析] 警告: data chunk 声明大小 {actual_data_size} 超过剩余字节 {remaining}，只跳过可用部分")
                        truncated = True
                    f.seek(skip_size, 1)
                    if skip_size % 2:
                        f.read(1)
                else:
                    f.seek(chunk_size, 1)
                    if chunk_size % 2:
                        f.read(1)
        
        if self.axml_data:
            self.adm = ADM(self.axml_data, self.chna_data)
            self.adm.parse()
        else:
            if truncated:
                print(f"[BW64解析] 警告: 未找到 axml chunk；文件被截断（缺少约 {truncated_missing} bytes），ADM 元数据可能位于缺失部分")
            else:
                print(f"[BW64解析] 警告: 未找到 axml chunk，该文件不是 ADM/BW64 格式")
        
        return self.adm
    
    def _parse_fmt_chunk(self, data: bytes) -> Dict:
        """解析 fmt chunk"""
        if len(data) < 16:
            return {}
        
        audio_format = struct.unpack('<H', data[0:2])[0]
        num_channels = struct.unpack('<H', data[2:4])[0]
        sample_rate = struct.unpack('<I', data[4:8])[0]
        bits_per_sample = struct.unpack('<H', data[14:16])[0] if len(data) > 14 else 16
        
        return {
            'format': audio_format,
            'channels': num_channels,
            'sample_rate': sample_rate,
            'bits': bits_per_sample
        }
    
    def iter_audio_blocks(self, block_samples: int = 48000, dtype: str = 'float32'):
        """
        流式分块读取音频数据。

        Args:
            block_samples: 每块采样数（按文件原始采样率）
            dtype: 读取数据类型

        Yields:
            (chunk, sample_rate): chunk 形状为 (samples, channels) 或 (samples,)
        """
        import soundfile as sf
        with sf.SoundFile(str(self.file_path), 'r') as f:
            sr = f.samplerate
            for chunk in f.blocks(blocksize=block_samples, dtype=dtype, always_2d=True):
                yield np.ascontiguousarray(chunk), sr

    def read_audio(self):
        """读取音频数据（一次性加载，小文件兼容接口）"""
        import soundfile as sf
        data, sr = sf.read(str(self.file_path), dtype='float32')
        return data, sr


def _scan_for_axml(f, file_size: int, actual_size: int, ds64_info: Optional[Dict[str, int]] = None) -> Tuple[bool, Optional[str]]:
    """在 WAVE/BW64 chunk 中扫描 axml chunk。
    
    支持 axml 位于 data chunk 之后的情况（常见于 BW64/RF64 ADM 文件）。
    返回 (是否找到 axml, 失败原因或 None)
    """
    scan_end = min(8 + file_size, actual_size)
    try:
        while f.tell() < scan_end:
            chunk_id = f.read(4)
            if len(chunk_id) < 4:
                if f.tell() >= actual_size:
                    return False, "已到达实际文件末尾，未找到 axml"
                break
            if chunk_id == b'axml':
                return True, None
            try:
                chunk_size_bytes = f.read(4)
                if len(chunk_size_bytes) < 4:
                    return False, "块大小读取失败"
                chunk_size = struct.unpack('<I', chunk_size_bytes)[0]
                # 大文件的 data chunk 可能使用 0xFFFFFFFF；使用 ds64 dataSize 跳过数据块后继续扫描
                if chunk_id == b'data' and chunk_size == 0xFFFFFFFF:
                    data_size = ds64_info.get('data_size', 0) if ds64_info else 0
                    if data_size > 0:
                        skip_size = min(data_size, scan_end - f.tell())
                        skip_size = min(skip_size, actual_size - f.tell())
                        f.seek(skip_size, 1)
                        if skip_size % 2:
                            f.read(1)
                        continue
                    return False, "遇到 64 位 data chunk 但缺少 ds64 dataSize"
                # 防止被截断文件中的超大 chunk_size 导致越界扫描
                remaining = scan_end - f.tell()
                if chunk_size > remaining:
                    truncated_missing = (8 + file_size) - actual_size if file_size > 0 else 0
                    msg = f"文件可能被截断：chunk {chunk_id!r} 声明大小 {chunk_size} 超过剩余字节 {remaining}"
                    if truncated_missing > 0:
                        msg += f"，声明文件大小比实际文件大小大 {truncated_missing} bytes"
                    return False, msg
                f.seek(chunk_size + (chunk_size % 2), 1)
            except Exception as e:
                return False, f"扫描块时出错: {e}"
    except Exception as e:
        return False, f"[is_adm_file] 扫描 axml 出错: {e}"
    return False, "已扫描完整文件，未找到 axml chunk"


def is_adm_file(file_path: str) -> bool:
    """检查文件是否为 ADM/BW64/RF64 格式"""
    path = Path(file_path)
    print(f"[is_adm_file] 被调用: {file_path}, 扩展名: {path.suffix}", flush=True)
    
    if path.suffix.lower() in ['.bw64', '.bwf', '.adm']:
        print(f"[is_adm_file] 扩展名匹配，直接返回 True", flush=True)
        return True
    
    try:
        actual_size = path.stat().st_size
        with open(path, 'rb') as f:
            header = f.read(12)
            riff_id = header[:4]
            declared_size = struct.unpack('<I', header[4:8])[0]
            print(f"[is_adm_file] 文件头: {riff_id}, format: {header[8:12]}, 32位size: {declared_size}, 实际大小: {actual_size}", flush=True)
            if riff_id in (b'BW64', b'RF64'):
                # BW64/RF64 都可能是 ADM 容器，但也可能只是大文件 WAV。
                # 必须实际检出 axml chunk 才认定为 ADM。
                print(f"[is_adm_file] {riff_id.decode('ascii')} 文件头，需扫描 axml chunk", flush=True)
                file_size = declared_size
                ds64_info = None
                if file_size == 0xFFFFFFFF:
                    f.seek(12)
                    ds64_info = _read_ds64_info_static(f)
                    if ds64_info is not None:
                        file_size = ds64_info['riff_size']
                    else:
                        print(f"[is_adm_file] 警告: {riff_id.decode('ascii')} 大文件但未找到 ds64 chunk，按非 ADM 处理", flush=True)
                        print(f"[is_adm_file] 最终返回 False", flush=True)
                        return False
                f.seek(12)
                result, reason = _scan_for_axml(f, file_size, actual_size, ds64_info)
                if result:
                    print(f"[is_adm_file] {riff_id.decode('ascii')} 文件包含 axml，返回 True", flush=True)
                else:
                    print(f"[is_adm_file] {riff_id.decode('ascii')} 文件未找到 axml，返回 False，原因: {reason}", flush=True)
                return result
            
            if riff_id == b'RIFF' and header[8:12] == b'WAVE':
                file_size = declared_size
                ds64_info = None
                
                # 大文件：32 位 size 为 0xFFFFFFFF，需要从 ds64 读取 64 位大小
                if file_size == 0xFFFFFFFF:
                    f.seek(12)
                    ds64_info = _read_ds64_info_static(f)
                    if ds64_info is not None:
                        file_size = ds64_info['riff_size']
                    else:
                        print(f"[is_adm_file] 警告: 大文件但未找到 ds64 chunk，按 4GB 处理", flush=True)
                
                # 检测文件截断
                truncated = file_size > 0 and 8 + file_size > actual_size
                if truncated:
                    missing = (8 + file_size) - actual_size
                    print(f"[is_adm_file] 警告: 声明文件大小 ({8 + file_size}) 大于实际文件大小 ({actual_size})，可能缺少 {missing} bytes 数据", flush=True)
                
                f.seek(12)
                result, reason = _scan_for_axml(f, file_size, actual_size, ds64_info)
                if result:
                    print(f"[is_adm_file] _scan_for_axml 返回: True", flush=True)
                else:
                    print(f"[is_adm_file] _scan_for_axml 返回: False, 原因: {reason}", flush=True)
                    # 文件被截断且无法找到 ADM 元数据时，抛出明确异常，供 GUI 提示用户
                    if truncated:
                        raise ValueError(reason or "文件不完整，无法找到 ADM 元数据")
                return result
    except Exception as e:
        print(f"[is_adm_file] 检查失败: {e}", flush=True)
        import traceback
        traceback.print_exc()
    
    print(f"[is_adm_file] 最终返回 False", flush=True)
    return False


def _read_ds64_info_static(f) -> Optional[Dict[str, int]]:
    """静态版本：读取 ds64 chunk 中的 64 位大小信息。
    
    返回 {'riff_size': int, 'data_size': int, 'sample_count': int}，
    如果没有 ds64 则返回 None。
    """
    start_pos = f.tell()
    try:
        while True:
            chunk_id = f.read(4)
            if len(chunk_id) < 4:
                break
            chunk_size_bytes = f.read(4)
            if len(chunk_size_bytes) < 4:
                break
            chunk_size = struct.unpack('<I', chunk_size_bytes)[0]
            
            if chunk_id == b'ds64':
                riff_size = struct.unpack('<Q', f.read(8))[0]
                data_size = struct.unpack('<Q', f.read(8))[0]
                sample_count = struct.unpack('<Q', f.read(8))[0]
                return {
                    'riff_size': riff_size,
                    'data_size': data_size,
                    'sample_count': sample_count
                }
            
            f.seek(chunk_size + (chunk_size % 2), 1)
    except Exception:
        pass
    finally:
        f.seek(start_pos)
    return None


def _read_ds64_size_static(f) -> Optional[int]:
    """静态版本：读取 ds64 chunk 中的 riffSize。"""
    ds64_info = _read_ds64_info_static(f)
    return ds64_info['riff_size'] if ds64_info else None
