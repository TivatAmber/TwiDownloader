import subprocess
from pathlib import Path
import asyncio
import concurrent.futures
import shutil
import requests
from TwiVideoDownloader.video import VideoDownloader
from TwiVideoDownloader.audio import AudioDownloader
from TwiVideoDownloader.total import M3U8Parser

class MediaDownloader:
    """媒体下载器，处理视频和音频的下载与合并"""
    def __init__(self, base_url: str, output_dir: str = "downloads", 
                 max_workers: int = 5, progress_callback=None, speed_callback=None):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.video_temp_dir = self.output_dir / "video_temp"
        self.audio_temp_dir = self.output_dir / "audio_temp"
        
        self.video_downloader = VideoDownloader(
            base_url, 
            str(self.video_temp_dir), 
            max_workers,
            progress_callback=lambda current, total: self._handle_progress("视频", current, total),
            speed_callback=self._handle_speed
        )
        self.audio_downloader = AudioDownloader(
            base_url, 
            str(self.audio_temp_dir), 
            max_workers,
            progress_callback=lambda current, total: self._handle_progress("音频", current, total),
            speed_callback=self._handle_speed
        )
        self.parser = M3U8Parser()
        self.session = requests.Session()
        self.progress_callback = progress_callback
        self.speed_callback = speed_callback

    async def download(self, m3u8_content: str) -> str:
        """下载并合并最高质量的视频和音频流"""
        try:
            self.video_temp_dir.mkdir(parents=True, exist_ok=True)
            self.audio_temp_dir.mkdir(parents=True, exist_ok=True)
            
            self.parser.parse(m3u8_content)
            best_stream = self.parser.get_highest_quality_stream()
            if not best_stream:
                raise ValueError("没有找到可用的视频流")
            
            audio_streams = self.parser.get_audio_streams()
            if not audio_streams:
                raise ValueError("没有找到可用的音频流")
            
            audio_stream = next(
                (audio for audio in audio_streams if audio.group_id == best_stream.audio),
                audio_streams[0]
            )
            
            video_m3u8 = self._download_m3u8(best_stream.uri)
            audio_m3u8 = self._download_m3u8(audio_stream.uri)
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                loop = asyncio.get_event_loop()
                video_future = loop.run_in_executor(executor, self.video_downloader.download, video_m3u8)
                audio_future = loop.run_in_executor(executor, self.audio_downloader.download, audio_m3u8)
                video_file, audio_file = await asyncio.gather(video_future, audio_future)
            
            output_filename = f"final_output_{best_stream.resolution}.mp4"
            output_path = self.output_dir / output_filename
            self._merge_video_audio(video_file, audio_file, str(output_path))
            
            return str(output_path)
            
        finally:
            self._cleanup_temp_dirs()

    def _download_m3u8(self, uri: str) -> str:
        """下载m3u8文件内容"""
        full_url = uri if uri.startswith('http') else f"{self.base_url.rstrip('/')}{uri}"
        response = self.session.get(full_url, timeout=30)
        response.raise_for_status()
        return response.text

    def _merge_video_audio(self, video_path: str, audio_path: str, output_path: str):
        """使用ffmpeg合并视频和音频"""
        command = [
            'ffmpeg',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'copy',
            '-y',
            output_path
        ]
        subprocess.run(command, check=True, capture_output=True)

    def _cleanup_temp_dirs(self):
        """清理临时目录"""
        try:
            if self.video_temp_dir.exists():
                shutil.rmtree(self.video_temp_dir)
            if self.audio_temp_dir.exists():
                shutil.rmtree(self.audio_temp_dir)
        except Exception as e:
            print(f"清理临时目录失败: {str(e)}")

    def _handle_progress(self, type_str: str, current: int, total: int):
        """处理进度回调"""
        if self.progress_callback:
            self.progress_callback(type_str, current, total)

    def _handle_speed(self, speed_str: str):
        """处理速度回调"""
        if self.speed_callback:
            self.speed_callback(speed_str)
