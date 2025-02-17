import sys
import asyncio
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLineEdit, QPushButton, QProgressBar,
    QLabel, QMessageBox
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
        
        self.base_url = "https://video.twimg.com"
        self.output_dir = "downloads"
        self.max_workers = 5
        
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        # 创建带进度回调的下载器
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
        # 计算总体进度
        progress = int((current / total) * 80) + 20  # 20-100范围
        self.progress_updated.emit(f"下载中...", progress)

    def handle_speed(self, speed_str: str):
        """处理速度回调"""
        self.speed_updated.emit(speed_str)

    async def download_video(self):
        try:
            # 获取m3u8内容
            self.progress_updated.emit("获取视频信息...", 0)
            m3u8_content = await self.fetcher.fetch_m3u8_content(self.url)
            
            # 下载视频
            self.progress_updated.emit("开始下载...", 20)
            output_file = await self.downloader.download(m3u8_content)
            
            self.progress_updated.emit("下载完成!", 100)
            self.download_complete.emit(output_file)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

    def run(self):
        """运行下载任务"""
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
        status_layout = QHBoxLayout()
        self.status_label = QLabel("准备就绪")
        self.speed_label = QLabel("")
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.speed_label)
        layout.addLayout(status_layout)
        
        # 总进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # 分片进度显示
        self.segment_label = QLabel("")
        layout.addWidget(self.segment_label)
        
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
        self.progress_bar.setValue(0)
        self.status_label.setText("准备下载...")
        self.speed_label.clear()
        self.segment_label.clear()
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
        self.progress_bar.setValue(value)

    def update_segment_progress(self, type_str: str, current: int, total: int):
        self.segment_label.setText(f"{type_str}: {current}/{total}")

    def update_speed(self, speed_str: str):
        self.speed_label.setText(speed_str)

    def download_finished(self, output_file: str):
        """下载完成处理"""
        self.status_label.setText("下载完成!")
        self.output_label.setText(f"文件保存在: {output_file}")
        self.enable_inputs()
        
        # 显示完成消息
        QMessageBox.information(self, "完成", "视频下载完成!")

    def handle_error(self, error_msg: str):
        """错误处理"""
        self.status_label.setText("下载失败")
        self.output_label.setText(f"错误: {error_msg}")
        self.enable_inputs()
        
        # 显示错误消息
        QMessageBox.critical(self, "错误", f"下载失败: {error_msg}")

    def enable_inputs(self):
        """重新启用输入控件"""
        self.download_btn.setEnabled(True)
        self.url_input.setEnabled(True)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
