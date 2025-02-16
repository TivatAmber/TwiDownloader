import asyncio
from pathlib import Path
from TwiVideoDownloader.media_downloader import MediaDownloader
from TwiVideoDownloader.fetch_source import VideoSourceFetcher

async def main():
    # 基本配置
    base_url = "https://video.twimg.com"
    output_dir = "downloads"
    max_workers = 5

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    downloader = MediaDownloader(base_url, output_dir, max_workers)
    fetcher = VideoSourceFetcher()
    
    try:
        tweet_url = input("请输入推文URL: ")
        m3u8_content = await fetcher.fetch_m3u8_content(tweet_url)
        output_file = await downloader.download(m3u8_content)
        print(f"下载完成! 文件保存在: {output_file}")
    except Exception as e:
        print(f"下载失败: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
