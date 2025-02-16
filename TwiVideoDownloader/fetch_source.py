import re
import json
import requests

class VideoSourceFetcher:
    # Twitter API公共token
    BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Authorization': f'Bearer {self.BEARER_TOKEN}'
        })

    async def fetch_m3u8_content(self, post_url):
        """获取Twitter视频的m3u8内容"""
        try:
            tweet_id = post_url.split('/')[-1]
            api_url = f'https://api.twitter.com/1.1/videos/tweet/config/{tweet_id}.json'
            
            response = self.session.get(api_url)
            response.raise_for_status()
            video_config = response.json()
            
            m3u8_url = video_config['track']['playbackUrl']
            m3u8_response = self.session.get(m3u8_url)
            m3u8_response.raise_for_status()
            return m3u8_response.text

        except requests.RequestException as e:
            raise Exception(f"获取m3u8内容失败: {str(e)}")
        except (KeyError, json.JSONDecodeError) as e:
            raise Exception(f"解析视频信息失败: {str(e)}")
        except Exception as e:
            raise Exception(f"处理过程中出错: {str(e)}")
