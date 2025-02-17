import asyncio
from pathlib import Path
from tqdm import tqdm
from TwiVideoDownloader.media_downloader import MediaDownloader
from TwiVideoDownloader.fetch_source import VideoSourceFetcher

class ProgressManager:
    """命令行进度显示管理器"""
    def __init__(self):
        self.video_pbar = None
        self.audio_pbar = None
        self.current_type = None
        self.speed_text = ""

    def handle_progress(self, type_str: str, current: int, total: int):
        """更新下载进度条"""
        if type_str != self.current_type:
            self.current_type = type_str
            if type_str == "视频":
                self.video_pbar = tqdm(total=total, desc="下载视频", unit="片段")
                self.video_pbar.n = current
            else:
                self.audio_pbar = tqdm(total=total, desc="下载音频", unit="片段")
                self.audio_pbar.n = current
        
        pbar = self.video_pbar if type_str == "视频" else self.audio_pbar
        pbar.n = current
        pbar.set_postfix_str(self.speed_text)
        pbar.refresh()

    def handle_speed(self, speed_str: str):
        """更新下载速度显示"""
        self.speed_text = speed_str
        if self.current_type:
            pbar = self.video_pbar if self.current_type == "视频" else self.audio_pbar
            pbar.set_postfix_str(speed_str)
            pbar.refresh()

    def close(self):
        """关闭进度条"""
        if self.video_pbar:
            self.video_pbar.close()
        if self.audio_pbar:
            self.audio_pbar.close()

async def main():
    base_url = "https://video.twimg.com"
    output_dir = "downloads"
    max_workers = 5

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    progress_mgr = ProgressManager()
    downloader = MediaDownloader(
        base_url, 
        output_dir, 
        max_workers,
        progress_callback=progress_mgr.handle_progress,
        speed_callback=progress_mgr.handle_speed
    )
    fetcher = VideoSourceFetcher()
    
    try:
        tweet_url = input("请输入推文URL: ")
        print("获取视频信息...")
        m3u8_content = await fetcher.fetch_m3u8_content(tweet_url)
        
        output_file = await downloader.download(m3u8_content)
        print(f"\n下载完成! 文件保存在: {output_file}")
    except Exception as e:
        print(f"\n下载失败: {str(e)}")
    finally:
        progress_mgr.close()

if __name__ == "__main__":
    asyncio.run(main())
