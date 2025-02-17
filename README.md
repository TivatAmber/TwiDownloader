# Twitter视频下载器

一个用于下载Twitter视频的工具，支持命令行和图形界面。

## 功能特点

- 支持下载Twitter视频
- 自动选择最高质量的视频和音频流
- 显示下载进度和速度
- 提供命令行和图形界面两种使用方式
- 支持并发下载，提高下载速度

## 安装要求

- Python 3.9 或更高版本
- FFmpeg（用于合并视频和音频）

## 安装方法

1. 安装 FFmpeg

   - Windows: 
     ```
     winget install ffmpeg
     ```
   - macOS:
     ```
     brew install ffmpeg
     ```
   - Linux:
     ```
     sudo apt install ffmpeg  # Ubuntu/Debian
     sudo dnf install ffmpeg  # Fedora
     ```

2. 安装 Python 包
   ```
   pip install .
   ```

## 使用方法

### 图形界面

运行以下命令启动图形界面：

```bash
python gui.py
```
或者
```bash
python cli.py
```

3. 输入推文URL
4. 下载完成

## 注意事项
- 推文URL需要是推特视频的URL，例如：https://x.com/dotey/status/1683738905412005888

## 更新日志
- 2025-02-16 初始化项目
- 2025-02-16 添加图形化界面下载

## 未来计划
- 添加字幕下载
- 添加自选下载
- ~~GUI界面~~

## 开发说明

### 环境配置
```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 安装依赖
pip install -e .
```

### 打包应用
```bash
# 安装打包工具
pip install pyinstaller

# 执行打包
python build.py
```

打包后的文件在 `dist` 目录中：
- `twi-dl-gui.exe` - Windows图形界面版本
- `twi-dl-cli.exe` - Windows命令行版本
- `twi-dl-gui` - Linux/Mac图形界面版本
- `twi-dl-cli` - Linux/Mac命令行版本

