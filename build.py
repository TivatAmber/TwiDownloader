import os
import shutil
import PyInstaller.__main__

def clean_build():
    """清理构建目录"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)

def build_gui():
    """打包图形界面版本"""
    PyInstaller.__main__.run([
        'gui.py',
        '--name=twi-dl-gui',
        '--windowed',
        '--onefile',
        '--clean',
        '--add-data=README.md:.',
        '--hidden-import=PyQt6',
        '--hidden-import=requests',
        '--hidden-import=ffmpeg-python',
        '--noupx',  # 禁用UPX压缩
        '--noconsole',  # 禁用控制台
    ])

def build_cli():
    """打包命令行版本"""
    PyInstaller.__main__.run([
        'cli.py',
        '--name=twi-dl-cli',
        '--onefile',
        '--clean',
        '--add-data=README.md:.',
        '--hidden-import=requests',
        '--hidden-import=ffmpeg-python',
    ])

if __name__ == "__main__":
    clean_build()
    build_gui()
    build_cli() 