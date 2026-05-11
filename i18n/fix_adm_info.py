#!/usr/bin/env python3
"""Add self.tr() to hardcoded Chinese strings in ADM info display."""

from pathlib import Path

src = Path(__file__).parent.parent / "src" / "main_gui.py"
text = src.read_text(encoding="utf-8")

# line 564
old = 'lines.append(f"📦 文件: {Path(file_path).name}")'
new = 'lines.append(self.tr("📦 文件: {name}").format(name=Path(file_path).name))'
text = text.replace(old, new, 1)

# line 570
old = 'lines.append(f"🎬 节目: {prog_name}")'
new = 'lines.append(self.tr("🎬 节目: {name}").format(name=prog_name))'
text = text.replace(old, new, 1)

# line 575
old = 'lines.append(f"📊 内容: {content_count}个Content, {object_count}个Object")'
new = 'lines.append(self.tr("📊 内容: {cc} 个 Content, {oc} 个 Object").format(cc=content_count, oc=object_count))'
text = text.replace(old, new, 1)

# line 582
old = 'lines.append(f"🔊 声床配置 ({len(direct_speakers)} DirectSpeakers):")'
new = 'lines.append(self.tr("🔊 声床配置 ({count} DirectSpeakers):").format(count=len(direct_speakers)))'
text = text.replace(old, new, 1)

# line 602
old = 'lines.append(f"⚠️ 包含 {len(objects_ch)} 个动态对象(Object)")'
new = 'lines.append(self.tr("⚠️ 包含 {count} 个动态对象 (Object)").format(count=len(objects_ch)))'
text = text.replace(old, new, 1)

# line 604-607 atmos_render_label
old = '''                self.atmos_render_label.setText(
                    f"检测到 {len(objects_ch)} 个动态对象，可选择渲染到目标声道布局后，点击“渲染并测量”测量。\n"
                    f"注意：点击中间面板“开始测量”将仅测量声道响度，不包含对象。"
                )'''
new = '''                self.atmos_render_label.setText(
                    self.tr("检测到 {count} 个动态对象，可选择渲染到目标声道布局后，点击“渲染并测量”测量。\n"
                            "注意：点击中间面板“开始测量”将仅测量声道响度，不包含对象。").format(count=len(objects_ch))
                )'''
text = text.replace(old, new, 1)

# line 628
old = 'lines.append(f"🎯 自动识别为: {description} ({ch_count}ch声床, 置信度{confidence:.0%})")'
new = 'lines.append(self.tr("🎯 自动识别为: {desc} ({ch_count} ch 声床, 置信度 {conf})").format(desc=description, ch_count=ch_count, conf=f"{confidence:.0%}"))'
text = text.replace(old, new, 1)

# line 640
old = 'lines.append(f"⚠️ 基于数量识别: {fallback} ({ch_count}ch)")'
new = 'lines.append(self.tr("⚠️ 基于数量识别: {fallback} ({ch_count} ch)").format(fallback=fallback, ch_count=ch_count))'
text = text.replace(old, new, 1)

# line 642
old = 'lines.append("   (特征识别失败，请手动确认)")'
new = 'lines.append(self.tr("   (特征识别失败，请手动确认)"))'
text = text.replace(old, new, 1)

# line 647
old = 'lines.append("🎛️ 渲染器与创作软件信息")'
new = 'lines.append(self.tr("🎛️ 渲染器与创作软件信息"))'
text = text.replace(old, new, 1)

# line 652
old = "r_text = f\"🎚️ {r_info.get('name', '未知渲染器')}\""
new = "r_text = self.tr('🎚️ {name}').format(name=r_info.get('name', self.tr('未知渲染器')))"
text = text.replace(old, new, 1)

# line 661
old = 'lines.append("🎚️ 未检测到渲染器信息")'
new = 'lines.append(self.tr("🎚️ 未检测到渲染器信息"))'
text = text.replace(old, new, 1)

# line 666
old = "a_text = f\"🛠️ {a_info.get('authoring_tool')}\""
new = "a_text = self.tr('🛠️ {tool}').format(tool=a_info.get('authoring_tool'))"
text = text.replace(old, new, 1)

# line 671
old = 'lines.append("🛠️ 未检测到创作软件")'
new = 'lines.append(self.tr("🛠️ 未检测到创作软件"))'
text = text.replace(old, new, 1)

# line 674
old = "lines.append(f\"📐 参考布局: {a_info['reference_layout']}\")"
new = "lines.append(self.tr('📐 参考布局: {layout}').format(layout=a_info['reference_layout']))"
text = text.replace(old, new, 1)

# line 676
old = 'lines.append("🛠️ 未检测到创作软件信息")'
new = 'lines.append(self.tr("🛠️ 未检测到创作软件信息"))'
text = text.replace(old, new, 1)

# line 635 fallback default
old = "fallback = cfg_map.get(ch_count, '未知')"
new = "fallback = cfg_map.get(ch_count, self.tr('未知'))"
text = text.replace(old, new, 1)

src.write_text(text, encoding="utf-8")
print("Done.")
