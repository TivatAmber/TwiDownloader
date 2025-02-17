from dataclasses import dataclass
from typing import List, Optional
import re
import os
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time

@dataclass
class VideoSegment:
    """视频片段信息"""
    duration: float  # 持续时间
    uri: str        # 片段URL
    start_time: int # 开始时间(ms)
    end_time: int   # 结束时间(ms)
    resolution: str # 视频分辨率

class VideoM3U8Parser:
    """视频M3U8文件解析器"""
    def __init__(self):
        self.version: int = 0
        self.target_duration: int = 0
        self.media_sequence: int = 0
        self.playlist_type: str = ""
        self.map_uri: Optional[str] = None
        self.segments: List[VideoSegment] = []
        self.resolution: str = ""
    
    def parse(self, content: str):
        """解析M3U8文件内容"""
        lines = content.strip().split('\n')
        current_start = 0
        resolution_pattern = r'/(\d+x\d+)/'
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            if line.startswith('#EXT-X-VERSION:'):
                self.version = int(line.split(':')[1])
            elif line.startswith('#EXT-X-TARGETDURATION:'):
                self.target_duration = int(line.split(':')[1])
            elif line.startswith('#EXT-X-MEDIA-SEQUENCE:'):
                self.media_sequence = int(line.split(':')[1])
            elif line.startswith('#EXT-X-PLAYLIST-TYPE:'):
                self.playlist_type = line.split(':')[1]
            elif line.startswith('#EXT-X-MAP:'):
                self.map_uri = re.search(r'URI="([^"]+)"', line).group(1)
                resolution_match = re.search(resolution_pattern, self.map_uri)
                if resolution_match:
                    self.resolution = resolution_match.group(1)
            elif line.startswith('#EXTINF:'):
                duration = float(line.split(':')[1].rstrip(','))
                uri = lines[i + 1].strip()
                end_time = current_start + int(duration * 1000)
                
                self.segments.append(VideoSegment(
                    duration=duration,
                    uri=uri,
                    start_time=current_start,
                    end_time=end_time,
                    resolution=self.resolution
                ))
                current_start = end_time

class VideoDownloader:
    """视频下载器"""
    def __init__(self, base_url: str, output_dir: str = "downloads", 
                 max_workers: int = 5, progress_callback=None, speed_callback=None):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.parser = VideoM3U8Parser()
        self.session = requests.Session()
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        self.speed_callback = speed_callback

    def download(self, m3u8_content: str) -> str:
        """下载并合并视频文件"""
        self.parser.parse(m3u8_content)
        
        init_file = None
        if self.parser.map_uri:
            init_file = self.output_dir / "init.mp4"
            self._download_file(self.parser.map_uri, init_file)
        
        download_tasks = []
        segment_files = []
        for i, segment in enumerate(self.parser.segments):
            segment_file = self.output_dir / f"segment_{i:04d}.m4s"
            segment_files.append(segment_file)
            download_tasks.append((segment.uri, segment_file))
        
        completed_segments = 0
        total_segments = len(download_tasks)
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self._download_file, uri, file_path): file_path
                for uri, file_path in download_tasks
            }
            
            start_time = time.time()
            downloaded_bytes = 0
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    bytes_downloaded = future.result()
                    downloaded_bytes += bytes_downloaded
                    completed_segments += 1
                    
                    if self.progress_callback:
                        self.progress_callback(completed_segments, total_segments)
                    
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 0 and self.speed_callback:
                        speed = downloaded_bytes / elapsed_time
                        speed_str = self._format_speed(speed)
                        self.speed_callback(speed_str)
                        
                except Exception as e:
                    print(f"下载文件 {file_path} 失败: {str(e)}")
                    raise
        
        output_file = self.output_dir / f"output_{self.parser.resolution}.mp4"
        self._merge_files(init_file, segment_files, output_file)
        
        cleanup_files = segment_files
        if init_file:
            cleanup_files.append(init_file)
        self._cleanup_files(cleanup_files)
        
        return str(output_file)

    def _download_file(self, uri: str, output_path: Path) -> int:
        """下载单个文件并返回下载的字节数"""
        full_url = uri if uri.startswith('http') else f"{self.base_url.rstrip('/')}{uri}"
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(full_url, timeout=30)
                response.raise_for_status()
                
                content = response.content
                with open(output_path, 'wb') as f:
                    f.write(content)
                return len(content)
            except (requests.RequestException, IOError) as e:
                if attempt == max_retries - 1:
                    raise
                continue

    def _format_speed(self, bytes_per_second: float) -> str:
        """格式化下载速度"""
        if bytes_per_second >= 1024 * 1024:
            return f"{bytes_per_second / (1024 * 1024):.1f} MB/s"
        elif bytes_per_second >= 1024:
            return f"{bytes_per_second / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_second:.1f} B/s"

    def _merge_files(self, init_file: Path, segment_files: List[Path], output_file: Path):
        """合并初始化片段和视频片段"""
        with open(output_file, 'wb') as outfile:
            if init_file:
                with open(init_file, 'rb') as infile:
                    outfile.write(infile.read())
            
            for segment_file in segment_files:
                with open(segment_file, 'rb') as infile:
                    outfile.write(infile.read())

    def _cleanup_files(self, files: List[Path]):
        """清理临时文件"""
        for file in files:
            if file.exists():
                file.unlink()