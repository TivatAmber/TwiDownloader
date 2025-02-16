from dataclasses import dataclass
from typing import List, Optional
import re
import subprocess
from pathlib import Path
from TwiVideoDownloader.video import VideoDownloader
from TwiVideoDownloader.audio import AudioDownloader

@dataclass
class MediaInfo:
    """媒体信息数据类"""
    type: str
    name: str
    group_id: str
    uri: str
    language: Optional[str] = None
    autoselect: bool = False
    default: bool = False
    characteristics: Optional[str] = None

@dataclass
class StreamInfo:
    """流信息数据类"""
    bandwidth: int
    resolution: str
    codecs: str
    subtitles: Optional[str]
    audio: str
    uri: str
    average_bandwidth: Optional[int] = None

class M3U8Parser:
    """M3U8文件解析器"""
    def __init__(self):
        self.media_items: List[MediaInfo] = []
        self.stream_items: List[StreamInfo] = []
    
    def parse(self, content: str):
        """解析M3U8内容"""
        lines = content.strip().split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.startswith('#EXT-X-MEDIA:'):
                self.media_items.append(self._parse_media_line(line))
            elif line.startswith('#EXT-X-STREAM-INF:'):
                self.stream_items.append(self._parse_stream_line(line, lines[i + 1]))
                i += 1
            i += 1
    
    def _parse_media_line(self, line: str) -> MediaInfo:
        """解析媒体行"""
        attrs = self._parse_attributes(line[13:])
        return MediaInfo(
            type=attrs.get('TYPE', ''),
            name=attrs.get('NAME', ''),
            group_id=attrs.get('GROUP-ID', ''),
            uri=attrs.get('URI', '').strip('"'),
            language=attrs.get('LANGUAGE', None),
            autoselect=attrs.get('AUTOSELECT', 'NO').upper() == 'YES',
            default=attrs.get('DEFAULT', 'NO').upper() == 'YES',
            characteristics=attrs.get('CHARACTERISTICS', None)
        )
    
    def _parse_stream_line(self, inf_line: str, uri_line: str) -> StreamInfo:
        """解析流信息行"""
        attrs = self._parse_attributes(inf_line[18:])
        return StreamInfo(
            bandwidth=int(attrs.get('BANDWIDTH', '0')),
            resolution=attrs.get('RESOLUTION', ''),
            codecs=attrs.get('CODECS', '').strip('"'),
            subtitles=attrs.get('SUBTITLES', None),
            audio=attrs.get('AUDIO', ''),
            uri=uri_line.strip(),
            average_bandwidth=int(attrs.get('AVERAGE-BANDWIDTH', '0'))
        )
    
    def _parse_attributes(self, attr_string: str) -> dict:
        """解析属性字符串"""
        attrs = {}
        pattern = r'([A-Z-]+)=(?:"([^"]*)"|\b([^,]*)\b)'
        matches = re.finditer(pattern, attr_string)
        
        for match in matches:
            key = match.group(1)
            value = match.group(2) if match.group(2) is not None else match.group(3)
            attrs[key] = value
        
        return attrs

    def get_highest_quality_stream(self) -> Optional[StreamInfo]:
        """获取最高质量的视频流"""
        if not self.stream_items:
            return None
        return max(self.stream_items, key=lambda x: x.bandwidth)

    def get_audio_streams(self) -> List[MediaInfo]:
        """获取所有音频流"""
        return [media for media in self.media_items if media.type == 'AUDIO']

    def get_subtitle_streams(self) -> List[MediaInfo]:
        """获取所有字幕流"""
        return [media for media in self.media_items if media.type == 'SUBTITLES']