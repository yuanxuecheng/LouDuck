<?xml version='1.0' encoding='utf-8'?>
<TS version="2.1" language="en_US">
<context>
    <name>ADMRenderWorker</name>
    <message>
        <location filename="../src/main_gui.py" line="581" />
        <source>正在初始化 ADM 渲染器（{n} 个对象）...</source>
        <translation>Initializing ADM renderer ({n} objects)...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="583" />
        <source>正在初始化 ADM 渲染器...</source>
        <translation>Initializing ADM renderer...</translation>
    </message>
</context>
<context>
    <name>DetailedMeasurementWorker</name>
    <message>
        <location filename="../src/main_gui.py" line="254" />
        <source>测量文件</source>
        <translation>Measurement File</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="257" />
        <source>准备音频...</source>
        <translation>Preparing audio...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="277" />
        <source>ADM文件</source>
        <translation>ADM File</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="285" />
        <source>多单声道文件</source>
        <translation>Multi-mono files</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="288" />
        <source>音频加载失败</source>
        <translation>Audio loading failed</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="294" />
        <source>初始化: {num_channels} ch, {actual_duration:.1f} s</source>
        <translation>Init: {num_channels} ch, {actual_duration:.1f} s</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="308" />
        <source>开始测量...</source>
        <translation>Starting measurement...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="327" />
        <source> | ⚡{ratio:.1f}x 实时</source>
        <translation> | ⚡{ratio:.1f}x realtime</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="347" />
        <source>测量已停止</source>
        <translation>Measurement stopped</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="425" />
        <source>分析文件完成</source>
        <translation>File analysis complete</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="460" />
        <source>加载多单声道... {current}/{total}</source>
        <translation>Loading multi-mono... {current}/{total}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="352" />
        <source>计算最终指标...</source>
        <translation>Calculating final metrics...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="365" />
        <source>整理结果...</source>
        <translation>Organizing results...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="383" />
        <source>完成</source>
        <translation>Done</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="406" />
        <source>加载中... {mb_loaded:.1f}/{mb_total:.1f} MB</source>
        <translation>Loading... {mb_loaded:.1f}/{mb_total:.1f} MB</translation>
    </message>
</context>
<context>
    <name>ExportOptionsDialog</name>
    <message>
        <location filename="../src/main_gui.py" line="193" />
        <source>导出选项</source>
        <translation>Export Options</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="200" />
        <source>导出格式:</source>
        <translation>Export Format:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="202" />
        <source>TXT (文本报告)</source>
        <translation>TXT (Text Report)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="202" />
        <source>JSON (结构化数据)</source>
        <translation>JSON (Structured Data)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="202" />
        <source>CSV (表格数据)</source>
        <translation>CSV (Tabular Data)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="206" />
        <source>详细程度:</source>
        <translation>Detail Level:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="208" />
        <source>总体概况 (节目响度/最大短时/最大瞬时/真峰值/LRA)</source>
        <translation>Summary (Program Loudness / Max Short-term / Max Momentary / True Peak / LRA)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="212" />
        <source>Excel导出将包含:
• 整体测量结果
• 每秒短时响度 (3秒滑动窗口)
• 每秒最大真峰值
• 超标数值以红色标注</source>
        <translation>Excel export includes:
• Overall measurement results
• Short-term loudness per second (3s sliding window)
• Maximum true peak per second
• Out-of-range values highlighted in red</translation>
    </message>
</context>
<context>
    <name>LoudnessCurveWidget</name>
    <message>
        <location filename="../src/main_gui.py" line="107" />
        <source>等待测量数据...</source>
        <translation>Waiting for measurement data...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="167" />
        <source>时间 (s)</source>
        <translation>Time (s)</translation>
    </message>
</context>
<context>
    <name>LoudnessMeterApp</name>
    <message>
        <location filename="../src/main_gui.py" line="901" />
        <location filename="../src/main_gui.py" line="2033" />
        <source>EasyImport 说明</source>
        <translation>EasyImport Help</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2035" />
        <source>EasyImport：
直接选择任意封装格式待测文件，自动识别
  ★ 多个单声道——自动完成文件-&gt;声道映射
  ★ 单个多声道——自动识别内部顺序
  ★ ADM BWF——解析元数据信息，提供目标声道格式选择及“渲染并测量”功能</source>
        <translation>EasyImport:
Select any packaged audio file to be tested; auto-recognition
  ★ Multiple mono files — automatic file-to-channel mapping
  ★ Single multichannel file — automatic internal order recognition
  ★ ADM BWF — parse metadata, provide target channel format selection and "Render &amp; Measure" function</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="696" />
        <source>正在解析 ADM...</source>
        <translation>Parsing ADM...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="690" />
        <location filename="../src/main_gui.py" line="1348" />
        <source>📋 声道匹配 ({matched}/{total} 已匹配)</source>
        <translation>📋 Channel Match ({matched}/{total} matched)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="703" />
        <source>[错误] 无法解析 ADM 元数据

可能原因：
1. 文件不是有效的 ADM/BW64 格式
2. XML 命名空间不匹配</source>
        <translation>[Error] Unable to parse ADM metadata

Possible causes:
1. The file is not a valid ADM/BW64 format
2. XML namespace mismatch</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="708" />
        <source>[警告] ADM 元数据解析为空

可能原因：
1. 命名空间检测失败
2. 文件不包含 ADM 数据</source>
        <translation>[Warning] ADM metadata parsing returned empty

Possible causes:
1. Namespace detection failed
2. The file does not contain ADM data</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="713" />
        <source>📦 文件: {name}</source>
        <translation>📦 File: {name}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="719" />
        <source>🎬 节目: {name}</source>
        <translation>🎬 Programme: {name}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="724" />
        <source>📊 内容: {cc} 个 Content, {oc} 个 Object</source>
        <translation>📊 Contents: {cc} Content(s), {oc} Object(s)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="731" />
        <source>🔊 声床配置 ({count} DirectSpeakers):</source>
        <translation>🔊 Bed Config ({count} DirectSpeakers):</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="751" />
        <source>⚠️ 包含 {count} 个动态对象 (Object)</source>
        <translation>⚠️ Contains {count} dynamic Object(s)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="778" />
        <source>🎯 自动识别为: {desc} ({ch_count} ch 声床, 置信度 {conf})</source>
        <translation>🎯 Auto-detected: {desc} ({ch_count} ch bed, confidence {conf})</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="785" />
        <source>未知</source>
        <translation>Unknown</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="789" />
        <location filename="../src/main_gui.py" line="998" />
        <location filename="../src/main_gui.py" line="1124" />
        <source>自动检测</source>
        <translation>Auto Detect</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="790" />
        <source>⚠️ 基于数量识别: {fallback} ({ch_count} ch)</source>
        <translation>⚠️ Fallback by count: {fallback} ({ch_count} ch)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="792" />
        <source>   (特征识别失败，请手动确认)</source>
        <translation>   (Feature recognition failed, please confirm manually)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="797" />
        <source>🎛️ 渲染器与创作软件信息</source>
        <translation>🎛️ Renderer &amp; Authoring Tool Info</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="802" />
        <source>🎚️ {name}</source>
        <translation>🎚️ {name}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="802" />
        <source>未知渲染器</source>
        <translation>Unknown Renderer</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="811" />
        <source>🎚️ 未检测到渲染器信息</source>
        <translation>🎚️ No renderer info detected</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="821" />
        <source>🛠️ 未检测到创作软件</source>
        <translation>🛠️ No authoring tool detected</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="824" />
        <source>📐 参考布局: {layout}</source>
        <translation>📐 Reference Layout: {layout}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="826" />
        <source>🛠️ 未检测到创作软件信息</source>
        <translation>🛠️ No authoring tool info detected</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="853" />
        <source>📁 输入</source>
        <translation>📁 Input</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="923" />
        <source>文件信息</source>
        <translation>File Info</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="934" />
        <location filename="../src/main_gui.py" line="1355" />
        <location filename="../src/main_gui.py" line="1803" />
        <source>未选择文件</source>
        <translation>No file selected</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="965" />
        <source>格式</source>
        <translation>Format</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="965" />
        <location filename="../src/main_gui.py" line="1206" />
        <source>声道</source>
        <translation>Channel</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="966" />
        <source>采样率</source>
        <translation>Sample Rate</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="966" />
        <source>位深</source>
        <translation>Bit Depth</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="967" />
        <source>时长</source>
        <translation>Duration</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="967" />
        <source>大小</source>
        <translation>Size</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="996" />
        <source>声道配置:</source>
        <translation>Channel Config:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1019" />
        <location filename="../src/main_gui.py" line="2385" />
        <source>ADM 信息</source>
        <translation>ADM Info</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1037" />
        <location filename="../src/main_gui.py" line="1813" />
        <source>ADM文件信息将显示在这里...</source>
        <translation>ADM file info will appear here...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1053" />
        <source>🎧 沉浸式音频渲染</source>
        <translation>🎧 Immersive Audio Render</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1071" />
        <source>检测到动态对象音频，可选择渲染到目标声道布局后测量响度。
注意：点击中间面板“开始测量”将仅测量声道响度，不包含对象。</source>
        <translation>Dynamic object-based audio detected. You may render to a target channel layout before measuring loudness.
Note: clicking "Start Measurement" in the middle panel measures channel loudness only, excluding objects.</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1077" />
        <source>目标布局:</source>
        <translation>Target Layout:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1092" />
        <source>🎯 渲染并测量</source>
        <translation>🎯 Render &amp; Measure</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1121" />
        <source>声道模板:</source>
        <translation>Channel Template:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1125" />
        <source>自定义</source>
        <translation>Custom</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1138" />
        <source>🎯 自动匹配</source>
        <translation>🎯 Auto Match</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1155" />
        <source>上移</source>
        <translation>Move Up</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1161" />
        <source>下移</source>
        <translation>Move Down</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1167" />
        <source>删除选中</source>
        <translation>Delete Selected</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1172" />
        <source>清空</source>
        <translation>Clear All</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="660" />
        <location filename="../src/main_gui.py" line="1188" />
        <source>📋 声道匹配 (双击声道可编辑)</source>
        <translation>📋 Channel Matching (double-click to edit)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1206" />
        <source>#</source>
        <translation>#</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1206" />
        <source>文件名</source>
        <translation>Filename</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1289" />
        <location filename="../src/main_gui.py" line="1826" />
        <location filename="../src/main_gui.py" line="1834" />
        <location filename="../src/main_gui.py" line="2063" />
        <source>提示</source>
        <translation>Tip</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1289" />
        <source>请先选择文件</source>
        <translation>Please select files first</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1474" />
        <source>文件错误</source>
        <translation>File Error</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1474" />
        <source>无法读取文件:
{err}</source>
        <translation>Cannot read file:
{err}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1468" />
        <source>不支持的文件</source>
        <translation>Unsupported File</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1468" />
        <source>无法识别该文件类型:
{name}</source>
        <translation>Cannot recognize file type:
{name}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1570" />
        <source>⚙️ 标准与进度</source>
        <translation>⚙️ Standard &amp; Progress</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1574" />
        <source>响度标准:</source>
        <translation>Loudness Standard:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1577" />
        <source>GY/T 282-2014 (中国广电-电视)</source>
        <translation>GY/T 282-2014 (China Radio &amp; TV)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1578" />
        <source>GY/T 377-2023 (中国广电-网络/嘈杂环境)</source>
        <translation>GY/T 377-2023 (China Online/Noisy Env)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1579" />
        <source>EBU R128 (欧洲广播)</source>
        <translation>EBU R128 (European Broadcasting)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1580" />
        <source>ATSC A/85 (美国电视)</source>
        <translation>ATSC A/85 (US Television)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1614" />
        <source>当前步骤:</source>
        <translation>Current Step:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1615" />
        <source>等待开始</source>
        <translation>Waiting to start</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1619" />
        <source>总进度:</source>
        <translation>Total Progress:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1629" />
        <source>▶ 开始测量</source>
        <translation>▶ Start Measurement</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1637" />
        <source>⏹ 停止测量</source>
        <translation>⏹ Stop Measurement</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1643" />
        <source>🧹 清空结果</source>
        <translation>🧹 Clear Results</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1654" />
        <source>📊 结果与导出</source>
        <translation>📊 Results &amp; Export</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1659" />
        <location filename="../src/main_gui.py" line="2404" />
        <source>指标</source>
        <translation>Metric</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1659" />
        <location filename="../src/main_gui.py" line="2404" />
        <source>数值</source>
        <translation>Value</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1666" />
        <source>节目响度(I)</source>
        <translation>Program Loudness (I)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1666" />
        <source>最大短时响度(S)</source>
        <translation>Max Short-term Loudness (S)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1666" />
        <source>最大瞬时响度(M)</source>
        <translation>Max Momentary Loudness (M)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1666" />
        <source>最大真峰值(TP)</source>
        <translation>Max True Peak (TP)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1666" />
        <location filename="../src/main_gui.py" line="2485" />
        <source>响度范围(LRA)</source>
        <translation>Loudness Range (LRA)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1676" />
        <location filename="../src/main_gui.py" line="2170" />
        <source>节目响度: --</source>
        <translation>Program Loudness: --</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1681" />
        <location filename="../src/main_gui.py" line="2172" />
        <source>峰值: --</source>
        <translation>Peak: --</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1687" />
        <location filename="../src/main_gui.py" line="2270" />
        <source>导出</source>
        <translation>Export</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1707" />
        <source>TXT: 文本报告 | JSON: 结构化数据
Excel: 包含每秒详细数据</source>
        <translation>TXT: Text report | JSON: Structured data
Excel: Includes per-second details</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1718" />
        <location filename="../src/main_gui.py" line="2174" />
        <source>就绪</source>
        <translation>Ready</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1779" />
        <source>目标: {target} LKFS (±{tol} LU)
峰值: {peak} dBTP</source>
        <translation>Target: {target} LKFS (±{tol} LU)
Peak: {peak} dBTP</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1826" />
        <source>请先选择 ADM 文件</source>
        <translation>Please select an ADM file first</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1834" />
        <source>该文件不包含动态对象音频，无需渲染。</source>
        <translation>This file does not contain dynamic object-based audio; no rendering needed.</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1841" />
        <source>🎧 正在渲染到 {layout}...</source>
        <translation>🎧 Rendering to {layout}...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1870" />
        <source>🎧 渲染完成</source>
        <translation>🎧 Render Complete</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1878" />
        <source>✓ 渲染: {name}</source>
        <translation>✓ Rendered: {name}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1895" />
        <source>🎧 渲染失败</source>
        <translation>🎧 Render Failed</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1899" />
        <source>渲染失败</source>
        <translation>Render Failed</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1899" />
        <source>渲染过程中出错:
{err}</source>
        <translation>Error during rendering:
{err}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1995" />
        <source>✓ {count} 个单声道文件</source>
        <translation>✓ {count} mono files</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2063" />
        <source>请先选择输入文件</source>
        <translation>Please select an input file first</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2100" />
        <source>{current:.1f}s/{total:.1f}s | ⚡{speed:.1f}x 实时 | {eta}</source>
        <translation>{current:.1f}s/{total:.1f}s | ⚡{speed:.1f}x realtime | {eta}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2111" />
        <source>完成</source>
        <translation>Done</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2133" />
        <source>节目响度: {status}</source>
        <translation>Program Loudness: {status}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2136" />
        <source>峰值: {status}</source>
        <translation>Peak: {status}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2139" />
        <source>完成 | 用时 {time:.1f}s</source>
        <translation>Done | Time elapsed {time:.1f}s</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1916" />
        <location filename="../src/main_gui.py" line="1948" />
        <location filename="../src/main_gui.py" line="2185" />
        <location filename="../src/main_gui.py" line="2186" />
        <source>错误</source>
        <translation>Error</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="754" />
        <source>⚠️ 检测到 {count} 个动态对象，可选择渲染到目标声道布局后，点击“渲染并测量”测量。
⚠️ 点击中间面板“开始测量”将仅测量声道响度，不包含对象。
⚠️ 本软件使用EAR（EBU ADM Renderer）作为渲染器，渲染结果可能与Dolby或Audio Vivid存在差异，渲染后的响度测量结果仅供参考。</source>
        <translation>⚠️ Detected {count} dynamic object(s). You can render to a target channel layout and click "Render &amp; Measure".
⚠️ Clicking "Start Measurement" in the center panel will only measure channel loudness, excluding objects.
⚠️ This software uses EAR (EBU ADM Renderer) as the renderer. Results may differ from Dolby or Audio Vivid and are for reference only.</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="881" />
        <source>📁 文件导入（EasyImport）</source>
        <translation>📁 File Import (EasyImport)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="981" />
        <location filename="../src/main_gui.py" line="1394" />
        <location filename="../src/main_gui.py" line="1403" />
        <location filename="../src/main_gui.py" line="1809" />
        <source>声道顺序: -</source>
        <translation>Channel order: -</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1390" />
        <source>声道顺序: {order}</source>
        <translation>Channel order: {order}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1431" />
        <source>{minutes}分{secs:02d}.{millis:03d}秒</source>
        <translation>{minutes}m {secs:02d}.{millis:03d}s</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1432" />
        <source>{minutes}分{secs:02d}秒</source>
        <translation>{minutes}m {secs:02d}s</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1433" />
        <source>{seconds:.2f}秒</source>
        <translation>{seconds:.2f}s</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1904" />
        <source>选择音频文件</source>
        <translation>Select Audio File</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1916" />
        <source>无法读取文件: {err}</source>
        <translation>Unable to read file: {err}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1948" />
        <source>无法读取文件 {name}: {err}</source>
        <translation>Unable to read file {name}: {err}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1952" />
        <source>声道错误</source>
        <translation>Channel Error</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1953" />
        <source>文件 {name} 不是单声道（{ch} 声道）。

多文件模式要求所有文件必须是单声道。</source>
        <translation>File {name} is not mono ({ch} channels).

Multi-file mode requires all files to be mono.</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1958" />
        <source>格式错误</source>
        <translation>Format Error</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1959" />
        <source>文件 {name} 不是 WAV 格式。

多文件模式仅支持 WAV。</source>
        <translation>File {name} is not in WAV format.

Multi-file mode only supports WAV.</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1973" />
        <source>以下文件时长与其他文件不一致：</source>
        <translation>The following files have inconsistent durations:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1977" />
        <source>多数文件时长: {duration}</source>
        <translation>Majority duration: {duration}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1979" />
        <source>请统一所有文件时长后重新导入测量。</source>
        <translation>Please unify all file durations before re-importing for measurement.</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1982" />
        <source>时长不一致</source>
        <translation>Duration Mismatch</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2157" />
        <source>已停止</source>
        <translation>Stopped</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2158" />
        <source>测量已停止</source>
        <translation>Measurement stopped</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2210" />
        <source>{count} 个单声道文件</source>
        <translation>{count} mono files</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2263" />
        <source>文本文件 (*.txt)</source>
        <translation>Text File (*.txt)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2264" />
        <source>JSON文件 (*.json)</source>
        <translation>JSON File (*.json)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2265" />
        <source>Excel文件 (*.xlsx)</source>
        <translation>Excel File (*.xlsx)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2314" />
        <source>已导出: {name}</source>
        <translation>Exported: {name}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2317" />
        <source>导出失败</source>
        <translation>Export Failed</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2317" />
        <source>导出失败: {err}</source>
        <translation>Export failed: {err}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2331" />
        <source>缺少依赖</source>
        <translation>Missing Dependency</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2331" />
        <source>请安装 openpyxl: pip install openpyxl</source>
        <translation>Please install openpyxl: pip install openpyxl</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2339" />
        <source>响度测量报告</source>
        <translation>Loudness Measurement Report</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2356" />
        <source>被测文件信息</source>
        <translation>File Under Test</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2362" />
        <source>测量时间</source>
        <translation>Measurement Time</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2363" />
        <source>文件路径</source>
        <translation>File Path</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2364" />
        <source>文件名称</source>
        <translation>File Name</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2367" />
        <source>渲染器</source>
        <translation>Renderer</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2369" />
        <source>创作软件</source>
        <translation>Authoring Software</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2371" />
        <source>参考布局</source>
        <translation>Reference Layout</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2374" />
        <source>声道 {channel}</source>
        <translation>Channel {channel}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2399" />
        <source>整体测量结果</source>
        <translation>Overall Results</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2404" />
        <source>单位</source>
        <translation>Unit</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2426" />
        <location filename="../src/main_gui.py" line="2447" />
        <location filename="../src/main_gui.py" line="2459" />
        <location filename="../src/main_gui.py" line="2468" />
        <location filename="../src/main_gui.py" line="2541" />
        <location filename="../src/main_gui.py" line="2589" />
        <source>合格</source>
        <translation>Pass</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2426" />
        <location filename="../src/main_gui.py" line="2468" />
        <location filename="../src/main_gui.py" line="2541" />
        <location filename="../src/main_gui.py" line="2589" />
        <source>超标</source>
        <translation>Fail</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2428" />
        <source>节目响度</source>
        <translation>Program Loudness</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2443" />
        <source>最大短时响度</source>
        <translation>Max Short-term Loudness</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2455" />
        <source>最大瞬时响度</source>
        <translation>Max Momentary Loudness</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2470" />
        <source>最大真峰值</source>
        <translation>Max True Peak</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2489" />
        <source>参考</source>
        <translation>Reference</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2496" />
        <source>测量时长</source>
        <translation>Measurement Duration</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2498" />
        <source>秒</source>
        <translation>s</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2511" />
        <source>每秒短时响度 (3秒滑动窗口)</source>
        <translation>Short-term Loudness per Second (3s sliding window)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2516" />
        <source>短时响度(LKFS)</source>
        <translation>Short-term Loudness (LKFS)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2555" />
        <source>每秒最大真峰值</source>
        <translation>Max True Peak per Second</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2516" />
        <location filename="../src/main_gui.py" line="2560" />
        <source>时间(秒)</source>
        <translation>Time (s)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2560" />
        <source>真峰值(dBTP)</source>
        <translation>True Peak (dBTP)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2404" />
        <location filename="../src/main_gui.py" line="2560" />
        <source>标准限值</source>
        <translation>Standard Limit</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2404" />
        <location filename="../src/main_gui.py" line="2516" />
        <location filename="../src/main_gui.py" line="2560" />
        <source>状态</source>
        <translation>Status</translation>
    </message>
</context>
<context>
    <name>ReportExporter</name>
    <message>
        <location filename="../src/report_exporter.py" line="53" />
        <source>      ITU-R BS.1770-5 Loudness Measurement Report</source>
        <translation>      ITU-R BS.1770-5 Loudness Measurement Report</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="56" />
        <source>测量时间: {time}</source>
        <translation>Measurement Time: {time}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="57" />
        <source>文件路径: {path}</source>
        <translation>File Path: {path}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="58" />
        <source>文件名称: {name}</source>
        <translation>File Name: {name}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="59" />
        <source>时长:     {duration}</source>
        <translation>Duration:     {duration}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="60" />
        <source>采样率:   {sr} Hz</source>
        <translation>Sample Rate:   {sr} Hz</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="61" />
        <source>声道数:   {ch}</source>
        <translation>Channels:   {ch}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="69" />
        <source>ADM 信息:</source>
        <translation>ADM Info:</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="74" />
        <source>渲染器:   {info}</source>
        <translation>Renderer:   {info}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="76" />
        <source>创作软件: {info}</source>
        <translation>Authoring Tool: {info}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="78" />
        <source>参考布局: {layout}</source>
        <translation>Reference Layout: {layout}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="85" />
        <source>多单声道文件列表:</source>
        <translation>Multi-Mono File List:</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="94" />
        <source>测量结果:</source>
        <translation>Measurement Results:</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="96" />
        <source>  节目响度:      {val:+.2f} LKFS</source>
        <translation>  Program Loudness:      {val:+.2f} LKFS</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="97" />
        <source>  最大短时响度:  {val:+.2f} LKFS</source>
        <translation>  Max Short-term Loudness:  {val:+.2f} LKFS</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="98" />
        <source>  最大瞬时响度:  {val:+.2f} LKFS</source>
        <translation>  Max Momentary Loudness:  {val:+.2f} LKFS</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="99" />
        <source>  最大真峰值:    {val:+.2f} dBTP</source>
        <translation>  Max True Peak:    {val:+.2f} dBTP</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="100" />
        <source>  响度范围:      {val:.2f} LU</source>
        <translation>  Loudness Range:      {val:.2f} LU</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="102" />
        <source>合规性:</source>
        <translation>Compliance:</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="103" />
        <source>  EBU R128:  {status}</source>
        <translation>  EBU R128:  {status}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="103" />
        <location filename="../src/report_exporter.py" line="104" />
        <source>通过</source>
        <translation>Pass</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="103" />
        <source>未通过</source>
        <translation>Fail</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="104" />
        <source>  真峰值:    {status}</source>
        <translation>  True Peak:    {status}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="104" />
        <source>超标</source>
        <translation>Fail</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="174" />
        <source>节目响度</source>
        <translation>Program Loudness</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="176" />
        <source>最大短时响度</source>
        <translation>Max Short-term Loudness</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="177" />
        <source>最大瞬时响度</source>
        <translation>Max Momentary Loudness</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="178" />
        <source>最大真峰值</source>
        <translation>Max True Peak</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="180" />
        <source>响度范围</source>
        <translation>Loudness Range</translation>
    </message>
</context>
<context><name>ADM</name><message><source>立体声</source><translation>Stereo</translation></message><message><source>5.1 环绕声</source><translation>5.1 Surround</translation></message><message><source>7.1 环绕声</source><translation>7.1 Surround</translation></message><message><source>5.1.4 沉浸式</source><translation>5.1.4 Immersive</translation></message><message><source>7.1.4 沉浸式</source><translation>7.1.4 Immersive</translation></message><message><source>7.1.2 沉浸式</source><translation>7.1.2 Immersive</translation></message><message><source>未找到声床</source><translation>No bed found</translation></message><message><source>未检测到渲染器信息</source><translation>No renderer information detected</translation></message><message><source>名称: {name}</source><translation>Name: {name}</translation></message><message><source>版本: {version}</source><translation>Version: {version}</translation></message><message><source>坐标模式: {mode}</source><translation>Coordinate mode: {mode}</translation></message><message><source>(基于内容推断)</source><translation>(Inferred from content)</translation></message><message><source>渲染器信息不完整</source><translation>Renderer information incomplete</translation></message><message><source>未检测到创作软件信息</source><translation>No authoring software information detected</translation></message><message><source>参考布局: {layouts}</source><translation>Reference layout: {layouts}</translation></message><message><source>未知</source><translation>Unknown</translation></message><message><source>渲染器: {name} (推断)</source><translation>Renderer: {name} (inferred)</translation></message><message><source>渲染器: {name}</source><translation>Renderer: {name}</translation></message><message><source>创作信息不完整</source><translation>Authoring information incomplete</translation></message></context><context><name>ITU1770Meter</name><message><source>流式响度测量</source><translation>Streaming loudness measurement</translation></message><message><source>计算集成响度</source><translation>Calculating integrated loudness</translation></message><message><source>计算响度范围</source><translation>Calculating loudness range</translation></message><message><source>整理结果</source><translation>Organizing results</translation></message><message><source>测量完成</source><translation>Measurement complete</translation></message></context></TS>