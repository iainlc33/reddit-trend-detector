# main.py - Simplified for Render cron job
import praw
import os
import time
import sqlite3
import re
import requests
from datetime import datetime

class RedditTrendDetector:
    def __init__(self):
        # Get credentials from Render environment variables
        self.reddit = praw.Reddit(
            client_id=os.environ.get('REDDIT_CLIENT_ID'),
            client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
            user_agent="TShirtTrendBot/1.0"
        )
        
        # Use Render's persistent disk (paid feature) or external database
        # For free tier, we'll use webhooks instead of database
        self.DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
        self.MIN_VELOCITY = int(os.environ.get('MIN_VELOCITY', '1000'))
        
        self.MONITORING_SUBREDDITS = [
            'all', 'memes', 'funny', 'gaming', 'sports'
        ]
        
        # Track posts in memory (resets each run)
        self.processed_posts = set()

    def send_discord_alert(self, post, velocity, reason):
        """Send alert to Discord (free alternative to email)"""
        embed = {
            "embeds": [{
                "title": f"🔥 T-Shirt Trend: {post.title[:100]}",
                "color": 0xFF0000,
                "fields": [
                    {"name": "Subreddit", "value": f"r/{post.subreddit.display_name}", "inline": True},
                    {"name": "Velocity", "value": f"{velocity:.0f}/hour", "inline": True},
                    {"name": "Score", "value": f"{post.score:,}", "inline": True},
                    {"name": "Reason", "value": reason, "inline": False},
                    {"name": "Link", "value": f"https://reddit.com{post.permalink}", "inline": False}
                ],
                "footer": {"text": f"Act fast! Posted {((time.time() - post.created_utc) / 3600):.1f} hours ago"}
            }]
        }
        
        requests.post(self.DISCORD_WEBHOOK, json=embed)
        print(f"Alert sent for: {post.title[:50]}...")

    def is_tshirt_worthy(self, post):
        """Quick check for t-shirt potential"""
        title_lower = post.title.lower()
        
        # Copyright risks
        avoid = ['disney', 'marvel', 'nike', 'nintendo', 'pokemon']
        if any(brand in title_lower for brand in avoid):
            return False, "Copyright risk"
        
        # T-shirt patterns
        patterns = [
            r'(?i)(me|my|i) when',
            r'(?i)nobody:',
            r'(?i)be like',
            r'(?i)pov:',
            r'(?i)that feeling when'
        ]
        
        for pattern in patterns:
            if re.search(pattern, post.title):
                return True, "Meme format match"
        
        # Short phrases
        word_count = len(post.title.split())
        if 3 <= word_count <= 10:
            return True, "Short quotable phrase"
            
        return False, "Not ideal for t-shirt"

    def calculate_simple_velocity(self, post):
        """Simple velocity calculation"""
        hours_old = (time.time() - post.created_utc) / 3600
        if hours_old > 0 and hours_old < 6:  # Focus on fresh content
            return post.score / hours_old
        return 0

    def scan(self):
        """Single scan run - perfect for cron job"""
        print(f"Starting scan at {datetime.now()}")
        alerts_sent = 0
        
        for sub_name in self.MONITORING_SUBREDDITS:
            try:
                subreddit = self.reddit.subreddit(sub_name)
                
                # Check rising posts
                for post in subreddit.rising(limit=20):
                    if post.id in self.processed_posts:
                        continue
                        
                    velocity = self.calculate_simple_velocity(post)
                    is_worthy, reason = self.is_tshirt_worthy(post)
                    
                    if velocity > self.MIN_VELOCITY and is_worthy:
                        self.send_discord_alert(post, velocity, reason)
                        self.processed_posts.add(post.id)
                        alerts_sent += 1
                        time.sleep(1)  # Avoid webhook rate limits
                
                time.sleep(2)  # Reddit rate limiting
                
            except Exception as e:
                print(f"Error scanning r/{sub_name}: {e}")
        
        print(f"Scan complete. Sent {alerts_sent} alerts.")

if __name__ == "__main__":
    detector = RedditTrendDetector()
    detector.scan()
      - key: MIN_VELOCITY
        value: 1000
