# main.py - Highly Selective T-Shirt Trend Detector
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
        self.MIN_VELOCITY = int(os.environ.get('MIN_VELOCITY', '800'))  # Lowered to catch more for GPT
        
        # Text-focused subreddits for shirt-worthy content
        self.MONITORING_SUBREDDITS = [
            'all',                  # Major viral content
            'brandnewsentence',     # New phrases being coined
            'suspiciouslyspecific', # Relatable exact scenarios  
            'antiwork',            # Work culture statements
            'nursing',             # Professional identity
            'teachers',            # Professional identity
            'conservative',        # Political movements
            'politics',            # Political movements
            'nfl',                 # Sports reactions
            'nba',                 # Sports reactions
            'soccer',              # Sports reactions
            'blackpeopletwitter',  # Cultural phrases
            'whitepeopletwitter',  # Cultural phrases
            'rareinsults',         # Creative phrases
            'wallstreetbets',      # Financial movements
        ]
        
        # Track processed posts
        self.processed_posts = set()

    def analyze_with_gpt(self, post, top_comments):
        """Ultra-selective GPT analysis for t-shirt potential"""
        headers = {
            'Authorization': f'Bearer {self.OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Get more comment context
        comment_context = "\n".join([f"- {comment.body[:150]}" for comment in top_comments[:10]])
        
        prompt = f"""You are evaluating text for t-shirt potential. Be VERY selective - only high-quality ideas that people would actually buy and wear.

Reddit Post: "{post.title}"
Subreddit: r/{post.subreddit.display_name}
Upvotes: {post.score:,}
Top comments:
{comment_context}

Evaluate strictly:

1. Can this stand alone on a shirt without explanation?
2. Does it express strong identity, belief, or emotion that someone would PAY to wear?
3. Is it a movement, rallying cry, or cultural statement (like "Let's Go Brandon", "Birds Aren't Real", "Diamond Hands")?
4. Would someone still understand and want this in 3-6 months?
5. Is it original enough to not already be on 100 shirts?

Consider these seller categories:
- Political/social movements
- Professional pride/humor ("Trust me, I'm a nurse")
- Generational identity  
- Sports fan reactions
- Relatable life statements
- Counter-culture positions

Score 1-10 (be harsh):
1-5: Generic, won't sell
6-7: Maybe niche appeal
8-9: Strong seller potential
10: Viral hit potential

Format:
SCORE: [number]
ANALYSIS: [2 sentences max on why it works/doesn't]
VARIATIONS: [If 8+, suggest 2 better versions]
TARGET: [If 8+, who specifically would buy this]"""

        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are an expert at identifying phrases that sell on t-shirts. Be very selective - most ideas are not good enough."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,  # Lower temperature for more consistent scoring
            "max_tokens": 250
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
                analysis_text = ""
                variations = ""
                target = ""
                
                for line in analysis.split('\n'):
                    if line.startswith('SCORE:'):
                        try:
                            score = int(line.split(':')[1].strip())
                        except:
                            score = 0
                    elif line.startswith('ANALYSIS:'):
                        analysis_text = line.split(':', 1)[1].strip()
                    elif line.startswith('VARIATIONS:'):
                        variations = line.split(':', 1)[1].strip()
                    elif line.startswith('TARGET:'):
                        target = line.split(':', 1)[1].strip()
                
                return score, analysis_text, variations, target
            else:
                print(f"GPT API error: {response.status_code}")
                return 0, "API error", "", ""
                
        except Exception as e:
            print(f"Error calling GPT: {e}")
            return 0, "Analysis failed", "", ""

    def send_discord_alert(self, post, velocity, score, analysis, variations, target):
        """High-quality Discord alert for 8+ scores only"""
        embed = {
            "embeds": [{
                "title": f"🔥 HIGH POTENTIAL: {post.title[:100]}",
                "color": 0x00FF00,  # Green for high potential
                "fields": [
                    {"name": "T-Shirt Score", "value": f"**{score}/10**", "inline": True},
                    {"name": "Velocity", "value": f"{velocity:.0f}/hour", "inline": True},
                    {"name": "Upvotes", "value": f"{post.score:,}", "inline": True},
                    {"name": "Analysis", "value": analysis[:300], "inline": False},
                ],
                "footer": {"text": f"r/{post.subreddit.display_name} • Act within 24 hours"}
            }]
        }
        
        # Add variations if provided
        if variations:
            embed["embeds"][0]["fields"].append({
                "name": "💡 Better Variations", 
                "value": variations[:300], 
                "inline": False
            })
        
        # Add target audience
        if target:
            embed["embeds"][0]["fields"].append({
                "name": "🎯 Target Buyers", 
                "value": target[:200], 
                "inline": False
            })
        
        # Add link
        embed["embeds"][0]["fields"].append({
            "name": "Source", 
            "value": f"[View on Reddit](https://reddit.com{post.permalink})", 
            "inline": False
        })
        
        requests.post(self.DISCORD_WEBHOOK, json=embed)
        print(f"🔥 HIGH SCORE ALERT: {score}/10 - {post.title[:50]}...")

    def is_worth_analyzing(self, post):
        """Pre-filter before expensive GPT call"""
        title_lower = post.title.lower()
        
        # Skip copyrighted brands
        avoid = ['disney', 'marvel', 'nike', 'nintendo', 'pokemon', 'coca-cola', 
                 'mcdonalds', 'star wars', 'harry potter', 'netflix', 'spotify']
        if any(brand in title_lower for brand in avoid):
            return False
            
        # Skip pure news/tragedy
        skip_terms = ['died', 'killed', 'arrested', 'convicted', 'sentenced',
                      'breaking:', 'update:', 'megathread']
        if any(term in title_lower for term in skip_terms):
            return False
            
        # Must have some engagement
        if post.num_comments < 20:
            return False
            
        # Skip if too long for a shirt
        if len(post.title) > 100:
            return False
            
        return True

    def calculate_velocity(self, post):
        """Calculate upvote velocity"""
        hours_old = (time.time() - post.created_utc) / 3600
        if 0.5 <= hours_old <= 24:  # Between 30 mins and 24 hours
            return post.score / hours_old
        return 0

    def scan(self):
        """Main scanning function - selective quality over quantity"""
        print(f"Starting selective scan at {datetime.now()}")
        analyzed_count = 0
        high_score_count = 0
        
        for sub_name in self.MONITORING_SUBREDDITS:
            try:
                subreddit = self.reddit.subreddit(sub_name)
                
                # Check hot and rising
                posts_to_check = []
                posts_to_check.extend(subreddit.hot(limit=10))
                posts_to_check.extend(subreddit.rising(limit=10))
                
                for post in posts_to_check:
                    if post.id in self.processed_posts:
                        continue
                    
                    velocity = self.calculate_velocity(post)
                    
                    if velocity > self.MIN_VELOCITY and self.is_worth_analyzing(post):
                        # Get more comments for better context
                        post.comment_sort = 'top'
                        post.comments.replace_more(limit=0)
                        top_comments = post.comments[:10]
                        
                        # Analyze with GPT
                        score, analysis, variations, target = self.analyze_with_gpt(post, top_comments)
                        
                        # ONLY alert for high scores (8+)
                        if score >= 8:
                            self.send_discord_alert(post, velocity, score, analysis, variations, target)
                            high_score_count += 1
                        
                        self.processed_posts.add(post.id)
                        analyzed_count += 1
                        
                        # Log medium scores for your own tracking
                        if 6 <= score < 8:
                            print(f"Medium potential ({score}/10): {post.title[:60]}")
                        
                        # Rate limiting
                        time.sleep(1)
                        
                        # Limit API calls per run (higher limit since we want quality)
                        if analyzed_count >= 20:
                            print("Reached analysis limit for this run")
                            break
                
                time.sleep(2)  # Reddit rate limiting
                
            except Exception as e:
                print(f"Error scanning r/{sub_name}: {e}")
        
        print(f"Scan complete. Analyzed {analyzed_count} posts. Found {high_score_count} high-potential ideas.")

if __name__ == "__main__":
    detector = RedditTrendDetector()
    detector.scan()
