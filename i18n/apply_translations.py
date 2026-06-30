#!/usr/bin/env python3
"""
批量填充 LouDuck_en.ts 中未翻译的条目。
用法: python apply_translations.py
"""

import xml.etree.ElementTree as ET
from pathlib import Path

TS_PATH = Path('LouDuck_en.ts')

# 中文源文 -> 英文翻译
TRANSLATIONS = {
    '正在初始化 ADM 渲染器（{n} 个对象）...': 'Initializing ADM renderer ({n} objects)...',
    '正在初始化 ADM 渲染器...': 'Initializing ADM renderer...',
    '多单声道文件': 'Multi-mono files',
    '测量已停止': 'Measurement stopped',
    '分析文件完成': 'File analysis complete',
    '加载多单声道... {current}/{total}': 'Loading multi-mono... {current}/{total}',
    '等待测量数据...': 'Waiting for measurement data...',
    '时间 (s)': 'Time (s)',
    '📋 声道匹配 ({matched}/{total} 已匹配)': '📋 Channel Match ({matched}/{total} matched)',
    '⏹ 停止测量': '⏹ Stop Measurement',
    '🧹 清空结果': '🧹 Clear Results',
    '⚠️ 检测到 {count} 个动态对象，可选择渲染到目标声道布局后，点击“渲染并测量”测量。\n'
    '⚠️ 点击中间面板“开始测量”将仅测量声道响度，不包含对象。\n'
    '⚠️ 本软件使用EAR（EBU ADM Renderer）作为渲染器，渲染结果可能与Dolby或Audio Vivid存在差异，渲染后的响度测量结果仅供参考。':
    '⚠️ Detected {count} dynamic object(s). You can render to a target channel layout and click "Render & Measure".\n'
    '⚠️ Clicking "Start Measurement" in the center panel will only measure channel loudness, excluding objects.\n'
    '⚠️ This software uses EAR (EBU ADM Renderer) as the renderer. Results may differ from Dolby or Audio Vivid and are for reference only.',
    '📁 文件导入（EasyImport）': '📁 File Import (EasyImport)',
    '声道顺序: -': 'Channel order: -',
    '声道顺序: {order}': 'Channel order: {order}',
    '{minutes}分{secs:02d}.{millis:03d}秒': '{minutes}m {secs:02d}.{millis:03d}s',
    '{minutes}分{secs:02d}秒': '{minutes}m {secs:02d}s',
    '{seconds:.2f}秒': '{seconds:.2f}s',
    '选择音频文件': 'Select Audio File',
    '无法读取文件: {err}': 'Unable to read file: {err}',
    '无法读取文件 {name}: {err}': 'Unable to read file {name}: {err}',
    '声道错误': 'Channel Error',
    '文件 {name} 不是单声道（{ch} 声道）。\n\n多文件模式要求所有文件必须是单声道。':
    'File {name} is not mono ({ch} channels).\n\nMulti-file mode requires all files to be mono.',
    '格式错误': 'Format Error',
    '文件 {name} 不是 WAV 格式。\n\n多文件模式仅支持 WAV。':
    'File {name} is not in WAV format.\n\nMulti-file mode only supports WAV.',
    '以下文件时长与其他文件不一致：': 'The following files have inconsistent durations:',
    '多数文件时长: {duration}': 'Majority duration: {duration}',
    '请统一所有文件时长后重新导入测量。': 'Please unify all file durations before re-importing for measurement.',
    '时长不一致': 'Duration Mismatch',
    '已停止': 'Stopped',
    '文本文件 (*.txt)': 'Text File (*.txt)',
    'JSON文件 (*.json)': 'JSON File (*.json)',
    'Excel文件 (*.xlsx)': 'Excel File (*.xlsx)',
    '响度测量报告': 'Loudness Measurement Report',
    '被测文件信息': 'File Under Test',
    '测量时间': 'Measurement Time',
    '文件路径': 'File Path',
    '文件名称': 'File Name',
    '渲染器': 'Renderer',
    '创作软件': 'Authoring Software',
    '参考布局': 'Reference Layout',
    '声道 {channel}': 'Channel {channel}',
    '整体测量结果': 'Overall Results',
    '单位': 'Unit',
    '合格': 'Pass',
    '超标': 'Fail',
    '节目响度': 'Program Loudness',
    '最大短时响度': 'Max Short-term Loudness',
    '最大瞬时响度': 'Max Momentary Loudness',
    '最大真峰值': 'Max True Peak',
    '参考': 'Reference',
    '测量时长': 'Measurement Duration',
    '秒': 's',
    '每秒短时响度 (3秒滑动窗口)': 'Short-term Loudness per Second (3s sliding window)',
    '短时响度(LKFS)': 'Short-term Loudness (LKFS)',
    '[错误] 无法解析 ADM 元数据\n\n可能原因：\n1. 文件不是有效的 ADM/BW64 格式\n2. XML 命名空间不匹配':
    '[Error] Unable to parse ADM metadata\n\nPossible causes:\n1. The file is not a valid ADM/BW64 format\n2. XML namespace mismatch',
    '[警告] ADM 元数据解析为空\n\n可能原因：\n1. 命名空间检测失败\n2. 文件不包含 ADM 数据':
    '[Warning] ADM metadata parsing returned empty\n\nPossible causes:\n1. Namespace detection failed\n2. The file does not contain ADM data',
    '🎚️ {name}': '🎚️ {name}',
    '✓ {name} (请在浏览中添加更多)': '✓ {name} (add more in browse)',
    '✓ {count} 个单声道文件': '✓ {count} mono files',
    '{current:.1f}s/{total:.1f}s | ⚡{speed:.1f}x 实时 | {eta}': '{current:.1f}s/{total:.1f}s | ⚡{speed:.1f}x realtime | {eta}',
    '完成 | 用时 {time:.1f}s': 'Done | Time elapsed {time:.1f}s',
    '{count} 个单声道文件': '{count} mono files',
    '已导出: {name}': 'Exported: {name}',
    '📁 文件导入（随意导）': '📁 File Import (EasyImport)',
}


def main():
    tree = ET.parse(TS_PATH)
    root = tree.getroot()
    updated = 0

    for context in root.findall('context'):
        for msg in context.findall('message'):
            src_el = msg.find('source')
            trans_el = msg.find('translation')
            if src_el is None or trans_el is None:
                continue
            src = src_el.text or ''
            if src in TRANSLATIONS:
                trans_el.text = TRANSLATIONS[src]
                trans_el.attrib.pop('type', None)
                updated += 1

    # 添加 lupdate 无法提取的 QCoreApplication.translate 上下文
    extra_contexts = {
        'ADM': {
            '立体声': 'Stereo',
            '5.1 环绕声': '5.1 Surround',
            '7.1 环绕声': '7.1 Surround',
            '5.1.4 沉浸式': '5.1.4 Immersive',
            '7.1.4 沉浸式': '7.1.4 Immersive',
            '7.1.2 沉浸式': '7.1.2 Immersive',
            '未找到声床': 'No bed found',
            '未检测到渲染器信息': 'No renderer information detected',
            '名称: {name}': 'Name: {name}',
            '版本: {version}': 'Version: {version}',
            '坐标模式: {mode}': 'Coordinate mode: {mode}',
            '(基于内容推断)': '(Inferred from content)',
            '渲染器信息不完整': 'Renderer information incomplete',
            '未检测到创作软件信息': 'No authoring software information detected',
            '参考布局: {layouts}': 'Reference layout: {layouts}',
            '未知': 'Unknown',
            '渲染器: {name} (推断)': 'Renderer: {name} (inferred)',
            '渲染器: {name}': 'Renderer: {name}',
            '创作信息不完整': 'Authoring information incomplete',
        },
        'ITU1770Meter': {
            '流式响度测量': 'Streaming loudness measurement',
            '计算集成响度': 'Calculating integrated loudness',
            '计算响度范围': 'Calculating loudness range',
            '整理结果': 'Organizing results',
            '测量完成': 'Measurement complete',
        },
    }

    existing_context_names = {ctx.find('name').text for ctx in root.findall('context') if ctx.find('name') is not None}

    for ctx_name, messages in extra_contexts.items():
        if ctx_name in existing_context_names:
            ctx_el = next(ctx for ctx in root.findall('context') if ctx.find('name') is not None and ctx.find('name').text == ctx_name)
        else:
            ctx_el = ET.SubElement(root, 'context')
            name_el = ET.SubElement(ctx_el, 'name')
            name_el.text = ctx_name

        existing_sources = {msg.find('source').text for msg in ctx_el.findall('message') if msg.find('source') is not None}
        for src, trans in messages.items():
            if src in existing_sources:
                continue
            msg_el = ET.SubElement(ctx_el, 'message')
            src_el = ET.SubElement(msg_el, 'source')
            src_el.text = src
            trans_el = ET.SubElement(msg_el, 'translation')
            trans_el.text = trans
            updated += 1

    tree.write(TS_PATH, encoding='utf-8', xml_declaration=True)
    print(f'[OK] Updated {updated} translations in {TS_PATH}')


if __name__ == '__main__':
    main()
