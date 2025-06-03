# main.py - Multi-Path T-Shirt Trend Detector
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
        
        # Different thresholds for different paths
        self.HIGH_VELOCITY_THRESHOLD = int(os.environ.get('HIGH_VELOCITY', '1500'))
        self.BUYING_SIGNAL_VELOCITY = int(os.environ.get('BUYING_VELOCITY', '300'))
        self.NORMAL_VELOCITY = int(os.environ.get('NORMAL_VELOCITY', '600'))
        
        # Massively expanded subreddit list
        self.MONITORING_SUBREDDITS = [
            # Major/Viral
            'all', 'popular', 'bestof',
            
            # Meme/Humor
            'memes', 'dankmemes', 'me_irl', 'meirl', '2meirl4meirl',
            'adviceanimals', 'funny', 'humor',
            
            # Text-based gems
            'brandnewsentence', 'suspiciouslyspecific', 'rareinsults',
            'showerthoughts', 'unpopularopinion', 'crazyideas',
            
            # Cultural/Identity  
            'blackpeopletwitter', 'whitepeopletwitter', 'scottishpeopletwitter',
            'latinopeopletwitter', 'asianpeopletwitter',
            
            # Professional/Life
            'antiwork', 'workreform', 'nursing', 'teachers', 'retailhell',
            'talesfromretail', 'talesfromyourserver', 'kitchenconfidential',
            'programmerhumor', 'sysadmin', 'accounting',
            
            # Relationships/Life stages
            'tinder', 'dating', 'marriage', 'parenting', 'daddit', 'mommit',
            'childfree', 'teenagers', 'college',
            
            # Sports (seasonal goldmines)
            'nfl', 'nba', 'soccer', 'football', 'baseball', 'hockey',
            'formula1', 'ufc', 'boxing', 'sports',
            
            # Gaming
            'gaming', 'pcmasterrace', 'playstation', 'xbox', 'nintendoswitch',
            
            # Political/Movement
            'politics', 'conservative', 'libertarian', 'politicalhumor',
            'latestagecapitalism', 'aboringdystopia',
            
            # Regional/Local
            'murica', 'straya', 'casualuk', 'britishproblems',
            'canadians', 'ireland',
            
            # Fandoms (careful with copyright)
            'freefolk', 'prequelmemes', 'lotrmemes', 'marvelmemes',
            
            # Reaction/Meta
            'murderedbywords', 'clevercomebacks', 'suicidebywords',
            'technicallythetruth', 'holup',
            
            # Finance/Crypto
            'wallstreetbets', 'cryptocurrency', 'bitcoin', 'superstonk',
            
            # Hobbies/Interests
            'fitness', 'gym', 'running', 'camping', 'gardening',
            'cooking', 'motorcycles', 'cars',
            
            # Weird/Niche
            'birdsarentreal', 'giraffesdontexist', 'wyomingdoesntexist'
        ]
        
        # Track processed posts
        self.processed_posts = set()

    def check_buying_signals(self, comments):
        """Check if people are asking for this on a shirt"""
        buying_phrases = [
            # Shirt variations
            "on a shirt", "on a t-shirt", "on a tshirt", "on a t shirt",
            "on a tee", "on a tee shirt", "on a teeshirt", "on my shirt",
            "on my t-shirt", "on a tank", "on a hoodie", "on merch",
            
            # Making/needing phrases
            "make this a shirt", "make this a t-shirt", "make this a tee",
            "needs to be a shirt", "needs to be on a shirt",
            "need this on a", "put this on a", "get this on a",
            "someone make this", "someone put this", "please make this",
            
            # Wanting/buying phrases  
            "i'd wear", "would wear", "i'd buy", "would buy",
            "i'll take", "ill take", "i want this", "i need this",
            "want one", "need one", "where can i", "where do i",
            "take my money", "shut up and take", "throwing money",
            
            # Purchase intent
            "10/10 would buy", "10/10 would wear", "would cop",
            "instant buy", "instabuy", "insta buy", "buying this",
            "link to buy", "link?", "w2c", "where to cop",
            
            # Merchandise specific
            "merch idea", "merch potential", "merchandise this",
            "this is merch", "perfect for merch", "great merch",
            
            # Wearing intent
            "wear the shit out of", "wear the hell out of",
            "wear this everywhere", "wear this daily",
            "rock this", "sport this", "flex this",
            
            # Gift ideas
            "getting this for", "buy this for my", "gift idea",
            "perfect gift", "christmas gift", "birthday gift"
        ]
        
        buying_count = 0
        quote_examples = []
        
        for comment in comments:
            comment_lower = comment.body.lower()
            if any(phrase in comment_lower for phrase in buying_phrases):
                buying_count += 1
                # Capture the comment as evidence
                if len(quote_examples) < 3:
                    quote_examples.append(comment.body[:100])
        
        return buying_count, quote_examples

    def determine_alert_path(self, post, velocity, buying_count):
        """Determine which path qualifies this post"""
        paths = []
        
        # Path 1: High velocity viral content
        if velocity >= self.HIGH_VELOCITY_THRESHOLD:
            paths.append("🚀 HIGH VELOCITY")
        
        # Path 2: Strong buying signals with lower velocity
        if buying_count >= 2 and velocity >= self.BUYING_SIGNAL_VELOCITY:
            paths.append("💰 BUYING SIGNALS")
        
        # Path 3: Medium velocity with any buying signal
        if buying_count >= 1 and velocity >= self.NORMAL_VELOCITY:
            paths.append("⭐ SIGNAL + VELOCITY")
        
        # Path 4: Normal threshold if very engaged
        if post.num_comments > 100 and velocity >= self.NORMAL_VELOCITY:
            paths.append("💬 HIGH ENGAGEMENT")
        
        return paths

    def analyze_with_gpt(self, post, top_comments, buying_count, buying_examples, alert_paths):
        """Ultra-selective GPT analysis for t-shirt potential"""
        headers = {
            'Authorization': f'Bearer {self.OPENAI_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Get more comment context
        comment_context = "\n".join([f"- {comment.body[:150]}" for comment in top_comments[:10]])
        
        # Add buying signals info to prompt if found
        buying_signal_text = ""
        if buying_count > 0:
            buying_signal_text = f"\n\nIMPORTANT: {buying_count} comments explicitly asking for this on a shirt!"
            if buying_examples:
                buying_signal_text += "\nExamples: " + " | ".join([f'"{ex}"' for ex in buying_examples[:2]])
        
        # Add path information
        path_text = f"\n\nQualified via: {', '.join(alert_paths)}"
        
        prompt = f"""You are evaluating text for t-shirt potential. Be VERY selective - only high-quality ideas that people would actually buy and wear.

Reddit Post: "{post.title}"
Subreddit: r/{post.subreddit.display_name}
Upvotes: {post.score:,}
{buying_signal_text}
{path_text}
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

If people are explicitly asking for this on shirts in the comments, that's a STRONG positive signal!

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
            "temperature": 0.3,
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

    def send_discord_alert(self, post, velocity, score, analysis, variations, target, alert_paths):
        """High-quality Discord alert for 8+ scores only"""
        # Emoji based on path
        path_emoji = "🔥"
        if "BUYING SIGNALS" in alert_paths[0]:
            path_emoji = "💰"
        elif "HIGH VELOCITY" in alert_paths[0]:
            path_emoji = "🚀"
        
        embed = {
            "embeds": [{
                "title": f"{path_emoji} HIGH POTENTIAL: {post.title[:100]}",
                "color": 0x00FF00,  # Green for high potential
                "fields": [
                    {"name": "T-Shirt Score", "value": f"**{score}/10**", "inline": True},
                    {"name": "Velocity", "value": f"{velocity:.0f}/hour", "inline": True},
                    {"name": "Alert Path", "value": "\n".join(alert_paths), "inline": True},
                    {"name": "Analysis", "value": analysis[:300], "inline": False},
                ],
                "footer": {"text": f"r/{post.subreddit.display_name} • {post.score:,} upvotes • Act within 24 hours"}
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
        print(f"{path_emoji} HIGH SCORE ALERT: {score}/10 via {alert_paths[0]} - {post.title[:50]}...")

    def is_worth_analyzing(self, post, velocity, has_buying_signals):
        """Pre-filter with multiple paths"""
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
            
        # Skip if too long for a shirt
        if len(post.title) > 100:
            return False
        
        # Multiple paths to qualify
        # Path 1: High velocity (viral content)
        if velocity >= self.HIGH_VELOCITY_THRESHOLD:
            return True
            
        # Path 2: Buying signals with lower velocity
        if has_buying_signals and velocity >= self.BUYING_SIGNAL_VELOCITY:
            return True
            
        # Path 3: Medium velocity with good engagement
        if velocity >= self.NORMAL_VELOCITY and post.num_comments >= 20:
            return True
            
        return False

    def calculate_velocity(self, post):
        """Calculate upvote velocity"""
        hours_old = (time.time() - post.created_utc) / 3600
        if 0.5 <= hours_old <= 24:  # Between 30 mins and 24 hours
            return post.score / hours_old
        return 0

    def scan(self):
        """Main scanning function - multi-path approach"""
        print(f"Starting multi-path scan at {datetime.now()}")
        print(f"Monitoring {len(self.MONITORING_SUBREDDITS)} subreddits")
        print(f"Thresholds - High: {self.HIGH_VELOCITY_THRESHOLD}, Buying: {self.BUYING_SIGNAL_VELOCITY}, Normal: {self.NORMAL_VELOCITY}")
        
        analyzed_count = 0
        high_score_count = 0
        posts_by_path = {"high_velocity": 0, "buying_signals": 0, "normal": 0}
        
        for sub_name in self.MONITORING_SUBREDDITS:
            try:
                subreddit = self.reddit.subreddit(sub_name)
                
                # Check hot and rising
                posts_to_check = []
                try:
                    posts_to_check.extend(subreddit.hot(limit=10))
                    posts_to_check.extend(subreddit.rising(limit=10))
                except:
                    continue  # Skip if subreddit is inaccessible
                
                for post in posts_to_check:
                    if post.id in self.processed_posts:
                        continue
                    
                    velocity = self.calculate_velocity(post)
                    
                    # Quick check for buying signals before full analysis
                    if velocity > 0:  # Has some velocity
                        # Quick scan of top few comments
                        post.comment_sort = 'top'
                        post.comments.replace_more(limit=0)
                        quick_comments = post.comments[:5]
                        
                        quick_buying_count, _ = self.check_buying_signals(quick_comments)
                        
                        if self.is_worth_analyzing(post, velocity, quick_buying_count > 0):
                            # Get full comments for GPT analysis
                            top_comments = post.comments[:10]
                            buying_count, buying_examples = self.check_buying_signals(top_comments)
                            
                            # Determine which paths this qualifies under
                            alert_paths = self.determine_alert_path(post, velocity, buying_count)
                            
                            if alert_paths:  # Qualified under at least one path
                                # Analyze with GPT
                                score, analysis, variations, target = self.analyze_with_gpt(
                                    post, top_comments, buying_count, buying_examples, alert_paths
                                )
                                
                                # Log the path
                                if "HIGH VELOCITY" in alert_paths[0]:
                                    posts_by_path["high_velocity"] += 1
                                elif "BUYING SIGNALS" in alert_paths[0]:
                                    posts_by_path["buying_signals"] += 1
                                else:
                                    posts_by_path["normal"] += 1
                                
                                # ONLY alert for high scores (8+)
                                if score >= 8:
                                    self.send_discord_alert(post, velocity, score, analysis, variations, target, alert_paths)
                                    high_score_count += 1
                                
                                # Log medium scores
                                elif 6 <= score < 8:
                                    print(f"   Medium potential ({score}/10) via {alert_paths[0]}: {post.title[:60]}")
                                
                                self.processed_posts.add(post.id)
                                analyzed_count += 1
                                
                                # Rate limiting
                                time.sleep(1)
                                
                                # Higher limit since we have more subreddits
                                if analyzed_count >= 30:
                                    print("Reached analysis limit for this run")
                                    print(f"Posts by path: {posts_by_path}")
                                    return
                    
                    self.processed_posts.add(post.id)
                
                time.sleep(1)  # Reddit rate limiting between subreddits
                
            except Exception as e:
                print(f"Error scanning r/{sub_name}: {e}")
        
        print(f"Scan complete. Analyzed {analyzed_count} posts. Found {high_score_count} high-potential ideas.")
        print(f"Posts by path: {posts_by_path}")

if __name__ == "__main__":
    detector = RedditTrendDetector()
    detector.scan()
