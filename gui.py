import sys
import asyncio
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLineEdit, QPushButton, QProgressBar,
    QLabel, QMessageBox, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from TwiVideoDownloader.media_downloader import MediaDownloader
from TwiVideoDownloader.fetch_source import VideoSourceFetcher

class DownloadWorker(QThread):
    """下载工作线程"""
    progress_updated = pyqtSignal(str, int)  # 状态和总进度
    segment_progress = pyqtSignal(str, int, int)  # 分片下载进度 (类型, 当前, 总数)
    speed_updated = pyqtSignal(str)  # 下载速度
    download_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self.downloader = None
        self.fetcher = None

    def init_downloader(self):
        """延迟初始化下载器"""
        if not self.downloader:
            self.base_url = "https://video.twimg.com"
            self.output_dir = "downloads"
            self.max_workers = 5
            
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)
            
            self.downloader = MediaDownloader(
                self.base_url, 
                self.output_dir, 
                self.max_workers,
                progress_callback=self.handle_progress,
                speed_callback=self.handle_speed
            )
            self.fetcher = VideoSourceFetcher()

    def handle_progress(self, type_str: str, current: int, total: int):
        """处理下载进度回调"""
        self.segment_progress.emit(type_str, current, total)
        
    def handle_speed(self, speed_str: str):
        """处理速度回调"""
        self.speed_updated.emit(speed_str)

    async def download_video(self):
        try:
            self.init_downloader()  # 开始下载时才初始化
            self.progress_updated.emit("获取视频信息...", 0)
            m3u8_content = await self.fetcher.fetch_m3u8_content(self.url)
            
            self.progress_updated.emit("开始下载...", 20)
            output_file = await self.downloader.download(m3u8_content)
            
            self.progress_updated.emit("下载完成!", 100)
            self.download_complete.emit(output_file)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

    def run(self):
        asyncio.run(self.download_video())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Twitter视频下载器")
        self.setMinimumWidth(500)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        
        # URL输入区域
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入Twitter视频链接")
        self.download_btn = QPushButton("下载")
        self.download_btn.clicked.connect(self.start_download)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.download_btn)
        layout.addLayout(url_layout)
        
        # 状态显示
        self.status_label = QLabel("准备就绪")
        layout.addWidget(self.status_label)
        
        # 视频下载进度组
        video_group = QGroupBox("视频下载进度")
        video_layout = QVBoxLayout()
        self.video_progress = QProgressBar()
        self.video_progress.setRange(0, 100)
        self.video_label = QLabel("0/0")
        self.video_speed = QLabel("")
        video_layout.addWidget(self.video_progress)
        video_layout.addWidget(self.video_label)
        video_layout.addWidget(self.video_speed)
        video_group.setLayout(video_layout)
        layout.addWidget(video_group)
        
        # 音频下载进度组
        audio_group = QGroupBox("音频下载进度")
        audio_layout = QVBoxLayout()
        self.audio_progress = QProgressBar()
        self.audio_progress.setRange(0, 100)
        self.audio_label = QLabel("0/0")
        self.audio_speed = QLabel("")
        audio_layout.addWidget(self.audio_progress)
        audio_layout.addWidget(self.audio_label)
        audio_layout.addWidget(self.audio_speed)
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)
        
        # 输出信息
        self.output_label = QLabel()
        self.output_label.setWordWrap(True)
        layout.addWidget(self.output_label)
        
        layout.addStretch()
        self.worker = None

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "错误", "请输入视频链接")
            return
        
        self.download_btn.setEnabled(False)
        self.url_input.setEnabled(False)
        self.video_progress.setValue(0)
        self.audio_progress.setValue(0)
        self.status_label.setText("准备下载...")
        self.video_label.setText("0/0")
        self.audio_label.setText("0/0")
        self.video_speed.clear()
        self.audio_speed.clear()
        self.output_label.clear()
        
        self.worker = DownloadWorker(url)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.segment_progress.connect(self.update_segment_progress)
        self.worker.speed_updated.connect(self.update_speed)
        self.worker.download_complete.connect(self.download_finished)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.start()

    def update_progress(self, status: str, value: int):
        self.status_label.setText(status)

    def update_segment_progress(self, type_str: str, current: int, total: int):
        progress = int((current / total) * 100)
        if type_str == "视频":
            self.video_progress.setValue(progress)
            self.video_label.setText(f"{current}/{total}")
        else:
            self.audio_progress.setValue(progress)
            self.audio_label.setText(f"{current}/{total}")

    def update_speed(self, speed_str: str):
        if self.video_progress.value() < 100 and self.audio_progress.value() == 0:
            self.video_speed.setText(speed_str)
        elif self.audio_progress.value() < 100:
            self.audio_speed.setText(speed_str)

    def download_finished(self, output_file: str):
        self.status_label.setText("下载完成!")
        self.output_label.setText(f"文件保存在: {output_file}")
        self.enable_inputs()
        QMessageBox.information(self, "完成", "视频下载完成!")

    def handle_error(self, error_msg: str):
        self.status_label.setText("下载失败")
        self.output_label.setText(f"错误: {error_msg}")
        self.enable_inputs()
        QMessageBox.critical(self, "错误", f"下载失败: {error_msg}")

    def enable_inputs(self):
        self.download_btn.setEnabled(True)
        self.url_input.setEnabled(True)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
