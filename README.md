# 🎵 Audio Metadata Copier

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/UI-PyQt6-41CD52?logo=qt)](https://www.riverbankcomputing.com/software/pyqt/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

**批量复制音频文件元数据（标签 + 封面）的桌面工具。** 

你是否遇到过这种情况：手上有同一首歌的多个格式版本（比如 FLAC 无损版和 MP3 便携版），但只有一份有完整的歌曲信息？Audio Metadata Copier 帮你一键将元数据从源文件同步到所有匹配的目标文件。

## ✨ 功能

| 功能 | 说明 |
|------|------|
| 📋 **元数据复制** | 标题、歌手、专辑、年份、曲目号、风格、作曲、版权等 14 个字段 |
| 🖼 **封面图复制** | 支持 MP3/FLAC/OGG/M4A 内嵌封面，自动转换格式 |
| 📂 **智能匹配** | 基于文件名子串自动匹配目标文件，支持递归扫描子目录 |
| 🎯 **手动指定** | 拖放单个目标文件，精确控制 |
| 🔄 **格式支持** | FLAC  MP3  OGG  M4A  |
| 📦 **备份保护** | 可选写入前自动创建 .bak 备份 |
| 🎨 **暗色主题** | 深蓝海洋配色的毛玻璃风格 UI，支持无边框拖拽 |
| 🚀 **异步处理** | QThread 后台线程，大批量操作不卡界面 |

### 支持的音频格式

| 格式 | 扩展名 | 元数据标准 | 封面支持 |
|------|--------|-----------|---------|
| MP3 | `.mp3` | ID3v2.3 | ✅ APIC 帧 |
| FLAC | `.flac` | Vorbis Comments | ✅ Picture |
| OGG Vorbis | `.ogg` `.oga` | Vorbis Comments | ✅ METADATA_BLOCK_PICTURE |
| M4A / AAC | `.m4a` `.mp4` | iTunes atoms | ✅ covr atom |
| WAV | `.wav` | RIFF INFO | ⚠️ 有限支持 |
| WMA | `.wma` | ASF | ⚠️ 只读, 封面有限 |

## 📸 截图

<!-- TODO: 添加截图 -->

## 🔧 安装

### 从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/Smilingcafe/audio_metadata_copier.git
cd audio_metadata_copier

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python main.py
```

### 打包为独立 EXE (Windows)

```bash
# 单文件模式
python build.py

# 文件夹模式（启动更快）
python build.py --folder

# 调试模式（保留控制台）
python build.py --debug

# 清理构建缓存
python build.py --clean
```

## 📖 使用

1. **选择源文件**：点击"浏览"或拖放包含完整元数据的音频文件
2. **预览元数据**：自动读取并显示源文件的标签信息
3. **选择目标目录**：自动填入源文件所在目录，也可手动修改
4. **筛选格式**：勾选要处理的目标音频格式（默认全选）
5. **扫描匹配**：点击"扫描匹配"查找目录下所有匹配的目标文件
6. **确认复制**：勾选结果列表中的目标文件，点击"开始复制元数据"

### 匹配规则

目标文件名（不含扩展名）必须**完整包含**源文件名作为子串：

```
源:  "周杰伦 - 晴天.flac"
匹配: "周杰伦 - 晴天.mp3"       ✅ 精确匹配
匹配: "周杰伦 - 晴天_伴奏.wav"  ✅ 子串匹配
不匹配: "周杰伦 - 晴天的故事.mp3" ❌ 不完整包含
```

## 🏗 项目结构

```
audio_metadata_copier/
├── main.py                  # 应用入口 + 启动诊断
├── build.py                 # PyInstaller 打包脚本
├── requirements.txt         # Python 依赖
├── src/
│   ├── core/
│   │   ├── metadata.py      # 元数据读写引擎 (读/写统一接口)
│   │   ├── matcher.py       # 文件扫描与智能匹配
│   │   └── charset_utils.py # 多编码兼容 (乱码修复)
│   └── gui/
│       ├── main_window.py   # 主窗口 (Fusion 暗色主题)
│       ├── theme.py         # 主题配色与样式表
│       ├── worker.py        # QThread 后台线程
│       └── title_bar.py     # 自定义标题栏
└── tests/                   # 测试 (待完善)
```

## 🔑 依赖

| 包 | 版本 | 用途 |
|----|------|------|
| [mutagen](https://github.com/quodlibet/mutagen) | ≥1.47.0 | 音频元数据读写 |
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) | ≥6.6.0 | GUI 框架 |
| [pyinstaller](https://pyinstaller.org/) | ≥6.0.0 | 打包工具 (仅开发) |

## 📄 许可证

本项目采用 **GNU Affero General Public License v3.0 (AGPL-3.0)**。

这意味着：
- ✅ 可以自由使用、修改、分发
- ✅ 可以用于商业用途
- ⚠️ **修改后如果通过网络提供服务，必须公开源代码**
- ⚠️ 分发修改版本必须使用相同许可证

详见 [LICENSE](LICENSE)。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request。

## ⚠️ 已知限制

- WAV 格式不支持内嵌封面图（RIFF 规范限制）
- WMA 写入支持有限（mutagen 的 ASF 实现较基础）
- 暂不支持 AIFF、DSD、Opus 等其他格式
- 超大文件夹（10000+ 文件）扫描性能未优化

---

> 🤖 本项目大部分代码由 AI（DeepSeek V4 预览版）辅助完成。
