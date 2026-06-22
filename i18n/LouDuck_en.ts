<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="en_US">
<context>
    <name>DetailedMeasurementWorker</name>
    <message>
        <location filename="../src/main_gui.py" line="140"/>
        <source>测量文件</source>
        <translation>Measurement File</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="143"/>
        <source>准备音频...</source>
        <translation>Preparing audio...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="154"/>
        <location filename="../src/main_gui.py" line="189"/>
        <source>加载: {name}</source>
        <translation>Loading: {name}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="156"/>
        <source>加载完成</source>
        <translation>Loading complete</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="163"/>
        <source>读取 ADM...</source>
        <translation>Reading ADM...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="165"/>
        <source>ADM 加载完成</source>
        <translation>ADM loaded</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="166"/>
        <source>ADM文件</source>
        <translation>ADM File</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="172"/>
        <source>分析文件...</source>
        <translation>Analyzing file...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="182"/>
        <source>分析: {name}</source>
        <translation>Analyzing: {name}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="196"/>
        <source>多单声道加载完成</source>
        <translation>Multi-mono loading complete</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="199"/>
        <source>音频加载失败</source>
        <translation>Audio loading failed</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="209"/>
        <source>初始化: {num_channels} ch, {actual_duration:.1f} s</source>
        <translation>Init: {num_channels} ch, {actual_duration:.1f} s</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="222"/>
        <source>开始测量...</source>
        <translation>Starting measurement...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="238"/>
        <source> | ⚡{ratio:.1f}x 实时</source>
        <translation> | ⚡{ratio:.1f}x realtime</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="240"/>
        <source>测量中... {current_block}/{total_blocks} 块{speed_str}</source>
        <translation>Measuring... {current_block}/{total_blocks} blocks{speed_str}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="245"/>
        <source>计算最终指标...</source>
        <translation>Calculating final metrics...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="258"/>
        <source>整理结果...</source>
        <translation>Organizing results...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="275"/>
        <source>完成</source>
        <translation>Done</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="313"/>
        <source>加载中... {mb_loaded:.1f}/{mb_total:.1f} MB</source>
        <translation>Loading... {mb_loaded:.1f}/{mb_total:.1f} MB</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="418"/>
        <source>加载: {name} ({current}/{total})</source>
        <translation>Loading: {name} ({current}/{total})</translation>
    </message>
</context>
<context>
    <name>ExportOptionsDialog</name>
    <message>
        <location filename="../src/main_gui.py" line="80"/>
        <source>导出选项</source>
        <translation>Export Options</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="87"/>
        <source>导出格式:</source>
        <translation>Export Format:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="89"/>
        <source>TXT (文本报告)</source>
        <translation>TXT (Text Report)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="89"/>
        <source>JSON (结构化数据)</source>
        <translation>JSON (Structured Data)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="89"/>
        <source>CSV (表格数据)</source>
        <translation>CSV (Tabular Data)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="93"/>
        <source>详细程度:</source>
        <translation>Detail Level:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="95"/>
        <source>总体概况 (节目响度/最大短时/最大瞬时/真峰值/LRA)</source>
        <translation>Summary (Program Loudness / Max Short-term / Max Momentary / True Peak / LRA)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="99"/>
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
    <name>LoudnessMeterApp</name>
    <message>
        <location filename="../src/main_gui.py" line="865"/>
        <source>📁 文件导入（随意导）</source>
        <translation>📁 File Import（EasyImport）</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="894"/>
        <source>EasyImport 说明</source>
        <translation>EasyImport Help</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="896"/>
        <source>EasyImport：
直接选择任意封装格式待测文件，自动识别
  ★ 多个单声道——自动完成文件-&gt;声道映射
  ★ 单个多声道——自动识别内部顺序
  ★ ADM BWF——解析元数据信息，提供目标声道格式选择及“渲染并测量”功能</source>
        <translation>EasyImport:
Select any packaged audio file to be tested; auto-recognition
  ★ Multiple mono files — automatic file-to-channel mapping
  ★ Single multichannel file — automatic internal order recognition
  ★ ADM BWF — parse metadata, provide target channel format selection and &quot;Render &amp; Measure&quot; function</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="550"/>
        <source>正在解析 ADM...</source>
        <translation>Parsing ADM...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="557"/>
        <source>[错误] 无法解析 ADM 元数据

可能原因：
1. 文件不是有效的 ADM/BW64 格式
2. XML 命名空间不匹配</source>
        <translation>[错误] 无法解析 ADM 元数据

可能原因：
1. 文件不是有效的 ADM/BW64 格式
2. XML 命名空间不匹配</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="562"/>
        <source>[警告] ADM 元数据解析为空

可能原因：
1. 命名空间检测失败
2. 文件不包含 ADM 数据</source>
        <translation>[警告] ADM 元数据解析为空

可能原因：
1. 命名空间检测失败
2. 文件不包含 ADM 数据</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="567"/>
        <source>📦 文件: {name}</source>
        <translation>📦 File: {name}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="573"/>
        <source>🎬 节目: {name}</source>
        <translation>🎬 Programme: {name}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="578"/>
        <source>📊 内容: {cc} 个 Content, {oc} 个 Object</source>
        <translation>📊 Contents: {cc} Content(s), {oc} Object(s)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="585"/>
        <source>🔊 声床配置 ({count} DirectSpeakers):</source>
        <translation>🔊 Bed Config ({count} DirectSpeakers):</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="605"/>
        <source>⚠️ 包含 {count} 个动态对象 (Object)</source>
        <translation>⚠️ Contains {count} dynamic Object(s)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="608"/>
        <source>检测到 {count} 个动态对象，可选择渲染到目标声道布局后，点击“渲染并测量”测量。
注意：点击中间面板“开始测量”将仅测量声道响度，不包含对象。</source>
        <translation>Detected {count} dynamic object(s). You may render to a target channel layout, then click "Render &amp; Measure".
Note: clicking "Start Measurement" in the middle panel measures channel loudness only, excluding objects.</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="631"/>
        <source>🎯 自动识别为: {desc} ({ch_count} ch 声床, 置信度 {conf})</source>
        <translation>🎯 Auto-detected: {desc} ({ch_count} ch bed, confidence {conf})</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="638"/>
        <source>未知</source>
        <translation>Unknown</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="642"/>
        <location filename="../src/main_gui.py" line="874"/>
        <location filename="../src/main_gui.py" line="1000"/>
        <source>自动检测</source>
        <translation>Auto Detect</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="643"/>
        <source>⚠️ 基于数量识别: {fallback} ({ch_count} ch)</source>
        <translation>⚠️ Fallback by count: {fallback} ({ch_count} ch)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="645"/>
        <source>   (特征识别失败，请手动确认)</source>
        <translation>   (Feature recognition failed, please confirm manually)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="650"/>
        <source>🎛️ 渲染器与创作软件信息</source>
        <translation>🎛️ Renderer &amp; Authoring Tool Info</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="655"/>
        <source>🎚️ {name}</source>
        <translation>🎚️ {name}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="655"/>
        <source>未知渲染器</source>
        <translation>Unknown Renderer</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="664"/>
        <source>🎚️ 未检测到渲染器信息</source>
        <translation>🎚️ No renderer info detected</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="674"/>
        <source>🛠️ 未检测到创作软件</source>
        <translation>🛠️ No authoring tool detected</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="677"/>
        <source>📐 参考布局: {layout}</source>
        <translation>📐 Reference Layout: {layout}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="679"/>
        <source>🛠️ 未检测到创作软件信息</source>
        <translation>🛠️ No authoring tool info detected</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="706"/>
        <source>📁 输入</source>
        <translation>📁 Input</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="730"/>
        <source>输入方式</source>
        <translation>Input Mode</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="744"/>
        <source>🎵 多单声道</source>
        <translation>🎵 Multi-Mono</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="745"/>
        <source>📁 单个多声道</source>
        <translation>📁 Single Multichannel</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="789"/>
        <source>文件信息</source>
        <translation>File Info</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="800"/>
        <location filename="../src/main_gui.py" line="1239"/>
        <location filename="../src/main_gui.py" line="1631"/>
        <source>未选择文件</source>
        <translation>No file selected</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="831"/>
        <source>格式</source>
        <translation>Format</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="831"/>
        <location filename="../src/main_gui.py" line="1082"/>
        <source>声道</source>
        <translation>Channel</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="832"/>
        <source>采样率</source>
        <translation>Sample Rate</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="832"/>
        <source>位深</source>
        <translation>Bit Depth</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="833"/>
        <source>时长</source>
        <translation>Duration</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="833"/>
        <source>大小</source>
        <translation>Size</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="847"/>
        <source>浏览...</source>
        <translation>Browse...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="872"/>
        <source>声道配置:</source>
        <translation>Channel Config:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="895"/>
        <source>ADM 信息</source>
        <translation>ADM Info</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="913"/>
        <location filename="../src/main_gui.py" line="1639"/>
        <source>ADM文件信息将显示在这里...</source>
        <translation>ADM file info will appear here...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="929"/>
        <source>🎧 沉浸式音频渲染</source>
        <translation>🎧 Immersive Audio Render</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="947"/>
        <source>检测到动态对象音频，可选择渲染到目标声道布局后测量响度。
注意：点击中间面板“开始测量”将仅测量声道响度，不包含对象。</source>
        <translation>Dynamic object-based audio detected. You may render to a target channel layout before measuring loudness.
Note: clicking "Start Measurement" in the middle panel measures channel loudness only, excluding objects.</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="953"/>
        <source>目标布局:</source>
        <translation>Target Layout:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="968"/>
        <source>🎯 渲染并测量</source>
        <translation>🎯 Render &amp; Measure</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="997"/>
        <source>声道模板:</source>
        <translation>Channel Template:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1001"/>
        <source>自定义</source>
        <translation>Custom</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1014"/>
        <source>🎯 自动匹配</source>
        <translation>🎯 Auto Match</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1031"/>
        <source>上移</source>
        <translation>Move Up</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1037"/>
        <source>下移</source>
        <translation>Move Down</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1043"/>
        <source>删除选中</source>
        <translation>Delete Selected</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1048"/>
        <source>清空</source>
        <translation>Clear All</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1064"/>
        <source>📋 声道匹配 (双击声道可编辑)</source>
        <translation>📋 Channel Matching (double-click to edit)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1082"/>
        <source>#</source>
        <translation>#</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1082"/>
        <source>文件名</source>
        <translation>Filename</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1173"/>
        <location filename="../src/main_gui.py" line="1650"/>
        <location filename="../src/main_gui.py" line="1658"/>
        <location filename="../src/main_gui.py" line="1724"/>
        <location filename="../src/main_gui.py" line="1838"/>
        <source>提示</source>
        <translation>Tip</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1173"/>
        <source>请先选择文件</source>
        <translation>Please select files first</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1325"/>
        <source>✓ {name} (请在浏览中添加更多)</source>
        <translation>✓ {name} (请在浏览中添加更多)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1345"/>
        <source>文件错误</source>
        <translation>File Error</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1345"/>
        <source>无法读取文件:
{err}</source>
        <translation>Cannot read file:
{err}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1348"/>
        <source>不支持的文件</source>
        <translation>Unsupported File</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1348"/>
        <source>无法识别该文件类型:
{name}</source>
        <translation>Cannot recognize file type:
{name}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1368"/>
        <source>Immersive Loudness</source>
        <translation>Immersive Loudness</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1391"/>
        <source>Channel auto-match, ADM analysis and render, Excel export</source>
        <translation>Channel auto-match, ADM analysis and render, Excel export</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1416"/>
        <source>⚙️ 标准与进度</source>
        <translation>⚙️ Standard &amp; Progress</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1420"/>
        <source>响度标准:</source>
        <translation>Loudness Standard:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1423"/>
        <source>GY/T 282-2014 (中国广电-电视)</source>
        <translation>GY/T 282-2014 (China Radio &amp; TV)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1424"/>
        <source>GY/T 377-2023 (中国广电-网络/嘈杂环境)</source>
        <translation>GY/T 377-2023 (China Online/Noisy Env)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1425"/>
        <source>EBU R128 (欧洲广播)</source>
        <translation>EBU R128 (European Broadcasting)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1426"/>
        <source>ATSC A/85 (美国电视)</source>
        <translation>ATSC A/85 (US Television)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1460"/>
        <source>当前步骤:</source>
        <translation>Current Step:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1461"/>
        <source>等待开始</source>
        <translation>Waiting to start</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1465"/>
        <source>总进度:</source>
        <translation>Total Progress:</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1475"/>
        <source>▶ 开始测量</source>
        <translation>▶ Start Measurement</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1485"/>
        <source>📊 结果与导出</source>
        <translation>📊 Results &amp; Export</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1490"/>
        <source>指标</source>
        <translation>Metric</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1490"/>
        <source>数值</source>
        <translation>Value</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1497"/>
        <source>节目响度(I)</source>
        <translation>Program Loudness (I)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1497"/>
        <source>最大短时响度(S)</source>
        <translation>Max Short-term Loudness (S)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1497"/>
        <source>最大瞬时响度(M)</source>
        <translation>Max Momentary Loudness (M)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1497"/>
        <source>最大真峰值(TP)</source>
        <translation>Max True Peak (TP)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1497"/>
        <source>响度范围(LRA)</source>
        <translation>Loudness Range (LRA)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1507"/>
        <source>节目响度: --</source>
        <translation>Program Loudness: --</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1512"/>
        <source>峰值: --</source>
        <translation>Peak: --</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1518"/>
        <source>导出</source>
        <translation>Export</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1538"/>
        <source>TXT: 文本报告 | JSON: 结构化数据
Excel: 包含每秒详细数据</source>
        <translation>TXT: Text report | JSON: Structured data
Excel: Includes per-second details</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1545"/>
        <source>就绪</source>
        <translation>Ready</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1605"/>
        <source>目标: {target} LKFS (±{tol} LU)
峰值: {peak} dBTP</source>
        <translation>Target: {target} LKFS (±{tol} LU)
Peak: {peak} dBTP</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1650"/>
        <source>请先选择 ADM 文件</source>
        <translation>Please select an ADM file first</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1658"/>
        <source>该文件不包含动态对象音频，无需渲染。</source>
        <translation>This file does not contain dynamic object-based audio; no rendering needed.</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1665"/>
        <source>🎧 正在渲染到 {layout}...</source>
        <translation>🎧 Rendering to {layout}...</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1683"/>
        <source>🎧 渲染完成</source>
        <translation>🎧 Render Complete</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1692"/>
        <source>✓ 渲染: {name}</source>
        <translation>✓ Rendered: {name}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1708"/>
        <source>🎧 渲染失败</source>
        <translation>🎧 Render Failed</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1712"/>
        <source>渲染失败</source>
        <translation>Render Failed</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1712"/>
        <source>渲染过程中出错:
{err}</source>
        <translation>Error during rendering:
{err}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1724"/>
        <source>请先选择输入方式</source>
        <translation>Please select an input mode first</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1780"/>
        <source>跳过文件</source>
        <translation>Skip File</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1780"/>
        <source>以下文件不是单声道或无法读取:
{files}</source>
        <translation>The following files are not mono or cannot be read:
{files}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1800"/>
        <source>✓ {count} 个单声道文件</source>
        <translation>✓ {count} 个单声道文件</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1832"/>
        <source>ADM错误</source>
        <translation>ADM Error</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1832"/>
        <source>ADM 错误: {err}</source>
        <translation>ADM Error: {err}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1838"/>
        <source>请先选择输入文件</source>
        <translation>Please select an input file first</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1874"/>
        <source>{current:.1f}s/{total:.1f}s | ⚡{speed:.1f}x 实时 | {eta}</source>
        <translation>{current:.1f}s/{total:.1f}s | ⚡{speed:.1f}x 实时 | {eta}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1885"/>
        <source>完成</source>
        <translation>Done</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1907"/>
        <source>节目响度: {status}</source>
        <translation>Program Loudness: {status}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1910"/>
        <source>峰值: {status}</source>
        <translation>Peak: {status}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1913"/>
        <source>完成 | 用时 {time:.1f}s</source>
        <translation>完成 | 用时 {time:.1f}s</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1921"/>
        <location filename="../src/main_gui.py" line="1922"/>
        <source>错误</source>
        <translation>Error</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="1952"/>
        <source>{count} 个单声道文件</source>
        <translation>{count} 个单声道文件</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2048"/>
        <source>已导出: {name}</source>
        <translation>已导出: {name}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2051"/>
        <source>导出失败</source>
        <translation>Export Failed</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2051"/>
        <source>导出失败: {err}</source>
        <translation>Export failed: {err}</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2065"/>
        <source>缺少依赖</source>
        <translation>Missing Dependency</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2065"/>
        <source>请安装 openpyxl: pip install openpyxl</source>
        <translation>Please install openpyxl: pip install openpyxl</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2289"/>
        <source>每秒最大真峰值</source>
        <translation>Max True Peak per Second</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2294"/>
        <source>时间(秒)</source>
        <translation>Time (s)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2294"/>
        <source>真峰值(dBTP)</source>
        <translation>True Peak (dBTP)</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2294"/>
        <source>标准限值</source>
        <translation>Standard Limit</translation>
    </message>
    <message>
        <location filename="../src/main_gui.py" line="2294"/>
        <source>状态</source>
        <translation>Status</translation>
    </message>
</context>
<context>
    <name>ReportExporter</name>
    <message>
        <location filename="../src/report_exporter.py" line="53"/>
        <source>      ITU-R BS.1770-5 Loudness Measurement Report</source>
        <translation>      ITU-R BS.1770-5 Loudness Measurement Report</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="56"/>
        <source>测量时间: {time}</source>
        <translation>Measurement Time: {time}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="57"/>
        <source>文件路径: {path}</source>
        <translation>File Path: {path}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="58"/>
        <source>文件名称: {name}</source>
        <translation>File Name: {name}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="59"/>
        <source>时长:     {duration}</source>
        <translation>Duration:     {duration}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="60"/>
        <source>采样率:   {sr} Hz</source>
        <translation>Sample Rate:   {sr} Hz</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="61"/>
        <source>声道数:   {ch}</source>
        <translation>Channels:   {ch}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="69"/>
        <source>ADM 信息:</source>
        <translation>ADM Info:</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="74"/>
        <source>渲染器:   {info}</source>
        <translation>Renderer:   {info}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="76"/>
        <source>创作软件: {info}</source>
        <translation>Authoring Tool: {info}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="78"/>
        <source>参考布局: {layout}</source>
        <translation>Reference Layout: {layout}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="85"/>
        <source>多单声道文件列表:</source>
        <translation>Multi-Mono File List:</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="94"/>
        <source>测量结果:</source>
        <translation>Measurement Results:</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="96"/>
        <source>  节目响度:      {val:+.2f} LKFS</source>
        <translation>  Program Loudness:      {val:+.2f} LKFS</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="97"/>
        <source>  最大短时响度:  {val:+.2f} LKFS</source>
        <translation>  Max Short-term Loudness:  {val:+.2f} LKFS</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="98"/>
        <source>  最大瞬时响度:  {val:+.2f} LKFS</source>
        <translation>  Max Momentary Loudness:  {val:+.2f} LKFS</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="99"/>
        <source>  最大真峰值:    {val:+.2f} dBTP</source>
        <translation>  Max True Peak:    {val:+.2f} dBTP</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="100"/>
        <source>  响度范围:      {val:.2f} LU</source>
        <translation>  Loudness Range:      {val:.2f} LU</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="102"/>
        <source>合规性:</source>
        <translation>Compliance:</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="103"/>
        <source>  EBU R128:  {status}</source>
        <translation>  EBU R128:  {status}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="103"/>
        <location filename="../src/report_exporter.py" line="104"/>
        <source>通过</source>
        <translation>Pass</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="103"/>
        <source>未通过</source>
        <translation>Fail</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="104"/>
        <source>  真峰值:    {status}</source>
        <translation>  True Peak:    {status}</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="104"/>
        <source>超标</source>
        <translation>Exceeds Limit</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="174"/>
        <source>节目响度</source>
        <translation>Program Loudness</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="176"/>
        <source>最大短时响度</source>
        <translation>Max Short-term Loudness</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="177"/>
        <source>最大瞬时响度</source>
        <translation>Max Momentary Loudness</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="178"/>
        <source>最大真峰值</source>
        <translation>Max True Peak</translation>
    </message>
    <message>
        <location filename="../src/report_exporter.py" line="180"/>
        <source>响度范围</source>
        <translation>Loudness Range</translation>
    </message>
</context>
</TS>
