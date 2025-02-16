from dataclasses import dataclass
from typing import List, Optional
import re
import os
import requests
from pathlib import Path
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm  # 添加进度条支持

@dataclass
class AudioSegment:
    duration: float
    uri: str
    start_time: int
    end_time: int

class AudioM3U8Parser:
    def __init__(self):
        self.version: int = 0
        self.target_duration: int = 0
        self.media_sequence: int = 0
        self.playlist_type: str = ""
        self.map_uri: Optional[str] = None
        self.segments: List[AudioSegment] = []
    
    def parse(self, content: str):
        lines = content.strip().split('\n')
        current_start = 0
        
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
            elif line.startswith('#EXTINF:'):
                duration = float(line.split(':')[1].rstrip(','))
                uri = lines[i + 1].strip()
                end_time = current_start + int(duration * 1000)
                self.segments.append(AudioSegment(
                    duration=duration,
                    uri=uri,
                    start_time=current_start,
                    end_time=end_time
                ))
                current_start = end_time

class AudioDownloader:
    def __init__(self, base_url: str, output_dir: str = "downloads", max_workers: int = 5):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.parser = AudioM3U8Parser()
        self.session = requests.Session()
        self.max_workers = max_workers  # 最大线程数

    def download(self, m3u8_content: str) -> str:
        """下载并合并音频文件，返回最终文件路径"""
        self.parser.parse(m3u8_content)
        
        # 下载初始化片段
        init_file = None
        if self.parser.map_uri:
            init_file = self.output_dir / "init.mp4"
            self._download_file(self.parser.map_uri, init_file)
        
        # 准备下载任务
        download_tasks = []
        segment_files = []
        for i, segment in enumerate(self.parser.segments):
            segment_file = self.output_dir / f"segment_{i:04d}.m4s"
            segment_files.append(segment_file)
            download_tasks.append((segment.uri, segment_file))
        
        # 使用线程池并发下载
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 创建future到文件路径的映射
            future_to_file = {
                executor.submit(self._download_file, uri, file_path): file_path
                for uri, file_path in download_tasks
            }
            
            # 使用tqdm创建进度条
            with tqdm(total=len(download_tasks), desc="下载音频片段") as pbar:
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        future.result()  # 获取结果，如果有异常会抛出
                        pbar.update(1)
                    except Exception as e:
                        print(f"下载文件 {file_path} 失败: {str(e)}")
                        raise  # 重新抛出异常
        
        # 合并文件
        output_file = self.output_dir / "output.mp4"
        self._merge_files(init_file, segment_files, output_file)
        
        # 清理临时文件
        cleanup_files = segment_files
        if init_file:
            cleanup_files.append(init_file)
        self._cleanup_files(cleanup_files)
        
        return str(output_file)

    def _download_file(self, uri: str, output_path: Path):
        """下载单个文件"""
        full_url = uri if uri.startswith('http') else f"{self.base_url.rstrip('/')}{uri}"
        
        # 添加重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(full_url, timeout=30)
                response.raise_for_status()
                
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return
            except (requests.RequestException, IOError) as e:
                if attempt == max_retries - 1:  # 最后一次尝试
                    raise
                continue

    def _merge_files(self, init_file: Path, segment_files: List[Path], output_file: Path):
        """合并初始化片段和音频片段"""
        with open(output_file, 'wb') as outfile:
            # 写入初始化片段
            if init_file:
                with open(init_file, 'rb') as infile:
                    outfile.write(infile.read())
            
            # 写入音频片段
            for segment_file in segment_files:
                with open(segment_file, 'rb') as infile:
                    outfile.write(infile.read())

    def _cleanup_files(self, files: List[Path]):
        """清理临时文件"""
        for file in files:
            if file.exists():
                file.unlink()
