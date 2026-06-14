# LouDuck

> 基于 ITU-R BS.1770-5 标准的沉浸式音频响度测量工具
> 支持立体声、环绕声、三维声（5.1.4、7.1.4 等）及 ADM BWF 文件

[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue)](https://github.com/yuanxuecheng/LouDuck)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 📋 功能特性

- **多格式支持**：WAV、FLAC、MP3、OGG 及 ADM BWF 文件
- **多声道配置**：立体声、5.1、7.1、5.1.4、7.1.4 等沉浸式音频格式
- **ADM 元数据解析**：自动识别音频定义模型（ADM）内容、声道配置、渲染器信息
- **响度测量**：
  - 集成响度（Integrated Loudness）
  - 最大短时响度（Maximum Momentary Loudness）
  - 最大瞬时响度（Maximum Short-term Loudness）
  - 最大真峰值（Maximum True Peak）
  - 响度范围（Loudness Range, LRA）
- **可视化报告**：xlsx导出、超标数值红色标注
- **多语言支持**：中文 / English（自动检测系统语言）

---

## 🚀 快速开始

### 下载预编译版本

| 平台 | 架构 | 下载 |
|------|------|------|
| macOS | Apple Silicon (M1/M2/M3/M4/M5) | [下载最新版](https://github.com/yuanxuecheng/LouDuck/releases) |
| macOS | Intel (x86_64) | [下载最新版](https://github.com/yuanxuecheng/LouDuck/releases) |
| Windows | x64 | [下载最新版](https://github.com/yuanxuecheng/LouDuck/releases) |

### macOS 安装

1. 下载对应架构的 ZIP 文件
2. 解压得到 `LouDuck.app`
3. 右键点击 → **"打开"**（首次运行需绕过 Gatekeeper）
4. 点击 **"仍要打开"**

> ⚠️ 由于未进行 Apple 签名，首次启动可能收到安全提示。如信任本软件，请按上述步骤操作。

### Windows 安装

1. 下载 `LouDuck-Windows-x64.zip`
2. 解压到任意目录
3. 运行 `LouDuck.exe`

---

## 🛠️ 从源码构建

### 环境要求

| 项目 | 版本 |
|------|------|
| Python | 3.9+ (macOS Intel) / 3.12+ (macOS Apple Silicon) |
| PySide6 | 6.5+ |
| NumPy | 1.23.5 (macOS Intel) / 2.x (Apple Silicon) |
| PyInstaller | 5.6.2 (macOS Intel) / 6.x (Apple Silicon) |

### 安装依赖

```bash
# 克隆仓库
git clone https://github.com/yuanxuecheng/LouDuck.git
cd LouDuck

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 EBU ADM Renderer（不在 PyPI 上）
pip install git+https://github.com/ebu/ebu_adm_renderer.git
```

### 运行开发版本

```bash
python src/main_gui.py
```

### 构建可执行文件

**macOS Apple Silicon：**
```bash
pyinstaller \
  --windowed \
  --target-arch arm64 \
  --name "LouDuck" \
  --hidden-import=ear \
  --hidden-import=scipy.special._cdflib \
  --add-data "src/renderers:renderers" \
  --add-data "assets:assets" \
  --add-data "$(python -c 'import ear; print(ear.__path__[0])'):ear" \
  src/main_gui.py
```

**macOS Intel：**
```bash
pyinstaller \
  --windowed \
  --target-arch x86_64 \
  --name "LouDuck" \
  --hidden-import=ear \
  --hidden-import=scipy.special._cdflib \
  --add-data "src/renderers:renderers" \
  --add-data "assets:assets" \
  --add-data "/Users/$USER/Library/Python/3.9/lib/python/site-packages/ear:ear" \
  src/main_gui.py
```

**Windows：**
```bash
pyinstaller \
  --windowed \
  --name "LouDuck" \
  --hidden-import=ear \
  --hidden-import=scipy.special._cdflib \
  --add-data "src/renderers;renderers" \
  --add-data "assets;assets" \
  src/main_gui.py
```

---

## 📊 使用指南

### 单文件模式

1. 点击 左侧面板的**"文件导入"**
2. 选择 WAV/FLAC/MP3/OGG 或 ADM BWF 文件
3. 选择声道配置（自动检测或手动选择）
4. 点击 中间面板的**"开始测量"**
5. 查看结果并导出 excel 报告

### 多单声道文件模式

1. 按住 `Cmd` (macOS) 或 `Ctrl` (Windows) 多选单声道 WAV 文件
2. 系统自动匹配声道标识（L、R、C、LFE、Ls、Rs 等）
3. 选择目标模板（Stereo/5.1/7.1/5.1.4/7.1.4）
4. 点击 **"开始测量"**

### ADM 文件处理

1. 导入 ADM BWF 文件
2. 自动解析 ADM 元数据：
   - 内容描述
   - 声道配置（自动识别 5.1.4 / 7.1.4 等）
   - 渲染器信息（Dolby Atmos / EBU 等）
3. 点击 左侧面板最下方的**"渲染并检测"** 完成响度测量

---

## 🖥️ 系统要求

### macOS

| 配置 | 最低要求 | 推荐配置 |
|------|---------|---------|
| 操作系统 | macOS 12.7 Monterey | macOS 14+ Sonoma |
| 处理器 | Intel Core i5 / Apple Silicon M1 | Apple Silicon M2+ |
| 内存 | 8 GB | 16 GB |
| 存储 | 500 MB 可用空间 | 1 GB |
| 显示 | 1280×800 | 1920×1080+ |

### Windows

| 配置 | 最低要求 | 推荐配置 |
|------|---------|---------|
| 操作系统 | Windows 10 64-bit | Windows 11 |
| 处理器 | Intel Core i5 / AMD Ryzen 5 | Intel Core i7 / AMD Ryzen 7 |
| 内存 | 8 GB | 16 GB |
| 存储 | 500 MB 可用空间 | 1 GB |

---

## 🏗️ 项目架构

```
LouDuck/
├── src/
│   ├── main_gui.py           # 主界面入口
│   ├── adm_parser.py         # ADM 元数据解析
│   ├── itu1770_meter.py      # ITU-R BS.1770 响度计算核心
│   ├── renderers/            # 音频渲染器
│   │   ├── ear_renderer.py   # EBU ADM Renderer 封装
│   │   └── ...
│   └── report_exporter.py    # CSV 报告导出
├── assets/                   # 图标、背景图等资源
├── i18n/                     # 多语言翻译文件
├── tests/                    # 单元测试
├── .github/workflows/        # CI/CD 自动化构建
│   ├── build-macos-arm64.yml   # Apple Silicon 构建
│   └── build-windows.yml       # Windows 构建
├── requirements.txt          # Python 依赖
├── README.md                 # 本文件
└── LICENSE                   # MIT 许可证
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送分支：`git push origin feature/AmazingFeature`
5. 打开 Pull Request

---

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) 开源。

---

## 🙏 致谢

- [EBU ADM Renderer](https://github.com/ebu/ebu_adm_renderer) - ADM 文件渲染引擎
- [ITU-R BS.1770-5](https://www.itu.int/rec/R-REC-BS.1770) - 国际响度标准
- [PySide6](https://doc.qt.io/qtforpython/) - Qt for Python 跨平台 GUI 框架

---

## 📧 联系作者

如有问题或建议，欢迎提交 [Issue](https://github.com/yuanxuecheng/LouDuck/issues)。

---

> **注意**：本项目为个人开发者作品，未经 Apple / Microsoft 官方签名。分发和使用请遵守当地法律法规。
