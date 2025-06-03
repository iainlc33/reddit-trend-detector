# main.py - Reddit Trend Detector with LLM Analysis
import praw
import os
import time
import re
import requests
from datetime import datetime
import json

class RedditTrendDetector:
    def __init__(self):
        # Reddit credentials
        self.reddit = praw.Reddit(
            client_id=os.environ.get('REDDIT_CLIENT_ID'),
            client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
            user_agent="TShirtTrendBot/1.0"
        )
        
        # API Keys and webhooks
        self.DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK')
        self.OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
        self.MIN_VELOCITY = int(os.environ.get('MIN_VELOCITY', '1500'))
        
        # Better subreddits for t-shirt trends
        self.MONITORING_SUBREDDITS = [
            'all',              # Still good for massive trends
            'starterpacks',     # Visual memes
            'me_irl',          # Relatable content
            'meirl',           # Alternative me_irl
            'blackpeopletwitter', # Cultural phrases
            'whitepeopletwitter', # Trending phrases
            'memes',           # General memes
            'dankmemes',       # Edgier memes
            'politicalhumor',  # Political movements
            'wallstreetbets',  # Financial movements
        ]
        
        # Track processed posts
        self.processed_posts = set()

    def analyze_with_gpt(self, post, top_comments):
        """Use GPT to analyze t-shirt potential"""
        headers = {
            'Authorization': f'Bearer {self.OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Get context from comments
        comment_context = "\n".join([f"- {comment.body[:100]}" for comment in top_comments[:5]])
        
        prompt = f"""Analyze this Reddit trend for t-shirt merchandise potential.

Title: {post.title}
Subreddit: r/{post.subreddit.display_name}
Upvotes: {post.score}
Top comments:
{comment_context}

Evaluate as a t-shirt design opportunity:

1. Is this a cultural movement, rallying cry, or identity statement? (Like "Let's Go Brandon", "OK Boomer", "Diamond Hands")
2. Would people wear this to express identity, humor, or belonging?
3. Is it memeable and shareable?
4. Does it have staying power beyond this week?

Rate 1-10 for t-shirt potential (10 = extremely sellable).
Explain in 2 sentences why it would/wouldn't work.
Suggest the best angle if it's worth pursuing.

Response format:
SCORE: [number]
REASON: [explanation]
ANGLE: [suggestion if score >= 7]"""

        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are an expert at identifying viral t-shirt trends and cultural movements."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 200
        }
        
        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result['choices'][0]['message']['content']
                
                # Parse the response
                score = 0
                reason = ""
                angle = ""
                
                for line in analysis.split('\n'):
                    if line.startswith('SCORE:'):
                        try:
                            score = int(line.split(':')[1].strip())
                        except:
                            score = 0
                    elif line.startswith('REASON:'):
                        reason = line.split(':', 1)[1].strip()
                    elif line.startswith('ANGLE:'):
                        angle = line.split(':', 1)[1].strip()
                
                return score, reason, angle
            else:
                print(f"GPT API error: {response.status_code}")
                return 0, "API error", ""
                
        except Exception as e:
            print(f"Error calling GPT: {e}")
            return 0, "Analysis failed", ""

    def send_discord_alert(self, post, velocity, score, reason, angle):
        """Enhanced Discord alert with GPT analysis"""
        # Color based on score
        color = 0x00FF00 if score >= 8 else 0xFFFF00 if score >= 6 else 0xFF0000
        
        embed = {
            "embeds": [{
                "title": f"{'🔥' if score >= 8 else '⭐' if score >= 6 else '❓'} {post.title[:100]}",
                "color": color,
                "fields": [
                    {"name": "Subreddit", "value": f"r/{post.subreddit.display_name}", "inline": True},
                    {"name": "Velocity", "value": f"{velocity:.0f}/hour", "inline": True},
                    {"name": "T-Shirt Score", "value": f"{score}/10", "inline": True},
                    {"name": "Analysis", "value": reason[:200], "inline": False},
                ],
                "footer": {"text": f"Posted {((time.time() - post.created_utc) / 3600):.1f} hours ago"}
            }]
        }
        
        # Add angle if score is high
        if score >= 7 and angle:
            embed["embeds"][0]["fields"].append({
                "name": "🎯 Design Angle", 
                "value": angle[:200], 
                "inline": False
            })
        
        # Add link
        embed["embeds"][0]["fields"].append({
            "name": "Link", 
            "value": f"[View on Reddit](https://reddit.com{post.permalink})", 
            "inline": False
        })
        
        requests.post(self.DISCORD_WEBHOOK, json=embed)
        print(f"Alert sent - Score: {score}/10 - {post.title[:50]}...")

    def is_worth_analyzing(self, post):
        """Pre-filter before expensive GPT call"""
        title_lower = post.title.lower()
        
        # Skip copyrighted brands
        avoid = ['disney', 'marvel', 'nike', 'nintendo', 'pokemon', 'coca-cola', 'mcdonalds']
        if any(brand in title_lower for brand in avoid):
            return False
            
        # Skip purely news items
        if any(news in title_lower for news in ['breaking:', 'died', 'killed', 'arrested']):
            return False
            
        # Must have decent engagement
        if post.num_comments < 25:
            return False
            
        return True

    def calculate_velocity(self, post):
        """Calculate upvote velocity"""
        hours_old = (time.time() - post.created_utc) / 3600
        if 0.5 <= hours_old <= 12:  # Between 30 mins and 12 hours old
            return post.score / hours_old
        return 0

    def scan(self):
        """Main scanning function"""
        print(f"Starting scan at {datetime.now()}")
        analyzed_count = 0
        
        for sub_name in self.MONITORING_SUBREDDITS:
            try:
                subreddit = self.reddit.subreddit(sub_name)
                
                # Check both rising and hot
                posts_to_check = []
                posts_to_check.extend(subreddit.rising(limit=15))
                posts_to_check.extend(subreddit.hot(limit=10))
                
                for post in posts_to_check:
                    if post.id in self.processed_posts:
                        continue
                    
                    velocity = self.calculate_velocity(post)
                    
                    if velocity > self.MIN_VELOCITY and self.is_worth_analyzing(post):
                        # Get top comments for context
                        post.comment_sort = 'top'
                        post.comments.replace_more(limit=0)
                        top_comments = post.comments[:5]
                        
                        # Analyze with GPT
                        score, reason, angle = self.analyze_with_gpt(post, top_comments)
                        
                        # Only alert for promising trends
                        if score >= 6:  # Lowered from 7 to catch more potentials
                            self.send_discord_alert(post, velocity, score, reason, angle)
                        
                        self.processed_posts.add(post.id)
                        analyzed_count += 1
                        
                        # Rate limiting
                        time.sleep(1)
                        
                        # Limit API calls per run
                        if analyzed_count >= 10:
                            print("Reached analysis limit for this run")
                            return
                
                time.sleep(2)  # Reddit rate limiting
                
            except Exception as e:
                print(f"Error scanning r/{sub_name}: {e}")
        
        print(f"Scan complete. Analyzed {analyzed_count} posts.")

if __name__ == "__main__":
    detector = RedditTrendDetector()
    detector.scan()
