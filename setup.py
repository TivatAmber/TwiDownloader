from setuptools import setup, find_packages

setup(
    name="TwiVideoDownloader",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'requests>=2.31.0',
        'tqdm>=4.66.0',
        'ffmpeg-python>=0.2.0',
        'PyQt6>=6.4.0',
    ],
    entry_points={
        'console_scripts': [
            'twi-dl-cli=cli:main',
        ],
        'gui_scripts': [
            'twi-dl-gui=gui:main',
        ],
    },
    author="Your Name",
    description="Twitter视频下载器",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    python_requires='>=3.9',
) 