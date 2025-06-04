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
        
        # Massively expanded subreddit list - focused on shirt-worthy content
        self.MONITORING_SUBREDDITS = [
            # High potential for shirt content
            'targetedshirts', 'brandnewsentence', 'suspiciouslyspecific',
            'showerthoughts', 'technicallythetruth', 'rareinsults',
            
            # Meme/Humor (but selective)
            'memes', 'dankmemes', 'me_irl', 'meirl', '2meirl4meirl',
            
            # Identity/Culture
            'blackpeopletwitter', 'whitepeopletwitter', 'scottishpeopletwitter',
            'latinopeopletwitter', 
            
            # Professional/Life identity
            'antiwork', 'nursing', 'teachers', 'programmerhumor',
            'talesfromretail', 'talesfromyourserver', 'kitchenconfidential',
            
            # Lifestyle/Hobbies
            'gym', 'running', 'motorcycles', 'gaming', 'pcmasterrace',
            
            # Relationships/Life stages
            'tinder', 'parenting', 'daddit', 'childfree',
            
            # Sports (focus on fan culture)
            'nfl', 'nba', 'soccer', 'formula1',
            
            # Weird/Niche movements
            'birdsarentreal', 'giraffesdontexist', 'wyomingdoesntexist',
            
            # Good for phrases
            'murderedbywords', 'clevercomebacks', 'suicidebywords',
            'crazyideas', 'unpopularopinion',
            
            # Specific communities with merch culture
            'wallstreetbets', 'superstonk', 'cryptocurrency',
            
            # Avoid news/politics heavy subs
            # Removed: politics, politicalhumor, news, worldnews, conservative, libertarian
        ]
        
        # Track processed posts
        self.processed_posts = set()

    def check_buying_signals(self, comments):
        """Check if people are asking for this on a shirt - EXPANDED"""
        buying_phrases = [
            # Direct shirt requests
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
            "perfect gift", "christmas gift", "birthday gift",
            
            # NEW: Identity/motto signals
            "this is my motto", "my new motto", "life motto",
            "stealing this", "using this", "my new philosophy",
            "this is me", "literally me", "story of my life",
            "personal attack", "i feel attacked", "calling me out",
            "new favorite saying", "quote of the year",
            "need this energy", "this energy", "mood",
            "spirit animal", "my aesthetic", "vibe"
        ]
        
        buying_count = 0
        quote_examples = []
        
        for comment in comments:
            comment_lower = comment.body.lower()
if any(phrase in comment_lower for phrase in buying_phrases):
    buying_count += 1
    # Log which phrase matched
    for phrase in buying_phrases:
        if phrase in comment_lower:
            print(f"   BUYING SIGNAL FOUND: '{phrase}' in comment: {comment.body[:150]}", flush=True)
            break
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

Evaluate strictly BY THESE CRITERIA:

1. Can this stand alone on a shirt without explanation?
2. Would someone wear this to signal who they are, what they believe, or how they feel?
3. Does it hit at least ONE of these:
   - Movement/rallying cry ("Let's Go Brandon")
   - Relatable struggle ("Running on coffee and anxiety")
   - Identity/lifestyle flex ("Plant dad")
   - Mood/attitude ("Not today, Satan")
   - Clever wordplay ("Fucking around is ≥ finding out")
   - Niche insider humor (programmer jokes, nurse life)
4. Avoid only if it's extremely generic (Live Laugh Love) or exact copies of overdone shirts. Clever variations on trending phrases are GOOD - prioritize current relevance over timeless appeal.

Consider these seller categories:
- Political/social movements (but not news headlines)
- Professional pride/humor ("Trust me, I'm a nurse")
- Generational identity  
- Sports fan reactions
- Relatable life statements
- Counter-culture positions
- Quirky philosophies
- Internet culture references

If people are using phrases like "this is my motto", "mood", "literally me", or asking for it on shirts, that's a STRONG signal!

Remember: "Fucking around is ≥ finding out" is GREAT shirt material - clever wordplay with attitude.

Score 1-10 (be fair but selective):
1-3: Generic, news, or questions
4-5: Okay phrase but not identity-driven
6-7: Good potential, would appeal to niche
8-9: Strong seller, clear identity/mood
10: Viral hit potential, perfect shirt phrase

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
                
                return score, analysis_text, variations, target, buying_examples
            else:
                print(f"GPT API error: {response.status_code}")
                return 0, "API error", "", ""
                
        except Exception as e:
            print(f"Error calling GPT: {e}")
            return 0, "Analysis failed", "", ""

    def send_discord_alert(self, post, velocity, score, analysis, variations, target, alert_paths, buying_count=0, buying_examples=None):
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

# Add buying signals if found
if buying_count > 0 and buying_examples:
    embed["embeds"][0]["fields"].append({
        "name": "💬 Buying Signals Found", 
        "value": "\n".join([f'> {ex[:100]}...' for ex in buying_examples[:3]]), 
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
        """Pre-filter with multiple paths - IMPROVED"""
        title_lower = post.title.lower()
        
        # Skip copyrighted brands
        avoid = ['disney', 'marvel', 'nike', 'nintendo', 'pokemon', 'coca-cola', 
                 'mcdonalds', 'star wars', 'harry potter', 'netflix', 'spotify']
        if any(brand in title_lower for brand in avoid):
            return False
            
        # Skip pure news/tragedy
        skip_terms = ['died', 'killed', 'arrested', 'convicted', 'sentenced',
                      'breaking:', 'update:', 'megathread', 'headline:']
        if any(term in title_lower for term in skip_terms):
            return False
            
        # Skip if too long for a shirt
        if len(post.title) > 100:
            return False
            
        # NEW: Skip single word or very short titles
        if len(post.title.split()) <= 2:
            return False
            
        # NEW: Skip questions (usually not shirt material)
        if post.title.strip().endswith('?') and any(q in title_lower for q in ['what', 'why', 'how', 'when', 'where', 'who']):
            return False
            
        # NEW: Skip personal stories
        if any(personal in title_lower for personal in ['my dad', 'my mom', 'my wife', 'my husband', 'my kid', 'my son', 'my daughter']):
            return False
            
        # NEW: Skip if it's clearly a news article (contains common news site patterns)
        news_patterns = ['judge finds', 'report:', 'study:', 'poll:', 'court rules', 'lawsuit', 'investigation']
        if any(pattern in title_lower for pattern in news_patterns):
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
        """Main scanning function - collect all, then analyze best"""
        print(f"Starting multi-path scan at {datetime.now()}", flush=True)
        print(f"Monitoring {len(self.MONITORING_SUBREDDITS)} subreddits", flush=True)
        print(f"Thresholds - High: {self.HIGH_VELOCITY_THRESHOLD}, Buying: {self.BUYING_SIGNAL_VELOCITY}, Normal: {self.NORMAL_VELOCITY}", flush=True)
        
        # Collect ALL qualifying posts first
        all_candidates = []
        subreddits_checked = 0
        
        print("Collecting posts from all subreddits...", flush=True)
        
        for sub_name in self.MONITORING_SUBREDDITS:
            try:
                print(f"  Checking r/{sub_name}...", flush=True)
                subreddit = self.reddit.subreddit(sub_name)
                subreddits_checked += 1
                
                # Check hot and rising
                posts_to_check = []
                try:
                    posts_to_check.extend(subreddit.rising(limit=15))
                    posts_to_check.extend(subreddit.hot(limit=5))
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
                        quick_comments = post.comments[:50]
                        
                        quick_buying_count, _ = self.check_buying_signals(quick_comments)
                        
                        if self.is_worth_analyzing(post, velocity, quick_buying_count > 0):
                            # Determine priority score for sorting
                            priority = velocity
                            if quick_buying_count > 0:
                                priority += 1000  # Boost posts with buying signals
                            
                            # Add to candidates list
                            all_candidates.append({
                                'post': post,
                                'velocity': velocity,
                                'buying_signals': quick_buying_count,
                                'priority': priority,
                                'subreddit': sub_name
                            })
                    
                    self.processed_posts.add(post.id)
                
                # Progress indicator every 10 subreddits
                if subreddits_checked % 10 == 0:
                    print(f"  Progress: Checked {subreddits_checked}/{len(self.MONITORING_SUBREDDITS)} subreddits, found {len(all_candidates)} candidates", flush=True)
                
                time.sleep(1)  # Reddit rate limiting between subreddits
                
            except Exception as e:
                print(f"ERROR scanning r/{sub_name}: {e}", flush=True)
        
        print(f"\nFinished collecting. Checked {subreddits_checked} subreddits, found {len(all_candidates)} total candidates", flush=True)
        
        # Sort by priority (highest first)
        print("Sorting candidates by priority...", flush=True)
        all_candidates.sort(key=lambda x: x['priority'], reverse=True)
        
        # Now analyze the TOP candidates
        analyzed_count = 0
        high_score_count = 0
        posts_by_path = {"high_velocity": 0, "buying_signals": 0, "normal": 0}
        
        print(f"\nAnalyzing top {min(30, len(all_candidates))} candidates...", flush=True)
        
        for candidate in all_candidates[:30]:  # Only analyze top 30
            post = candidate['post']
            velocity = candidate['velocity']
            
            try:
                # Get full comments for GPT analysis
                post.comment_sort = 'top'
                post.comments.replace_more(limit=0)
                top_comments = post.comments[:50]
                buying_count, buying_examples = self.check_buying_signals(top_comments)
                
                # Determine which paths this qualifies under
                alert_paths = self.determine_alert_path(post, velocity, buying_count)
                
                if alert_paths:  # Should always have paths since we pre-filtered
                    # Analyze with GPT
                   score, analysis, variations, target, buying_examples = self.analyze_with_gpt(
    post, top_comments, buying_count, buying_examples, alert_paths
)
                    
                    # Log the path
                    if "HIGH VELOCITY" in alert_paths[0]:
                        posts_by_path["high_velocity"] += 1
                    elif "BUYING SIGNALS" in alert_paths[0]:
                        posts_by_path["buying_signals"] += 1
                    else:
                        posts_by_path["normal"] += 1
                    
                    # Alert for good scores (7+)
                    if score >= 7:
                        self.send_discord_alert(post, velocity, score, analysis, variations, target, alert_paths, buying_count, buying_examples)
                        high_score_count += 1
                    
                    # Log medium scores
                    elif 6 <= score < 7:
                        print(f"   Medium potential ({score}/10) via {alert_paths[0]}: {post.title[:60]}")
                    
                    # Log lower scores too for visibility
                    else:
                        print(f"   Low potential ({score}/10): {post.title[:60]}")
                    
                    analyzed_count += 1
                    
                    # Rate limiting
                    time.sleep(1)
                    
            except Exception as e:
                print(f"Error analyzing post: {e}")
        
        # Summary statistics
        print(f"\n=== SCAN COMPLETE ===")
        print(f"Subreddits checked: {subreddits_checked}/{len(self.MONITORING_SUBREDDITS)}")
        print(f"Total candidates found: {len(all_candidates)}")
        print(f"Posts analyzed: {analyzed_count}")
        print(f"High-potential ideas (7+): {high_score_count}")
        print(f"Posts by path: {posts_by_path}")
        
        # Show what we missed if any
        if len(all_candidates) > 30:
            print(f"\nTop 5 posts we didn't analyze:")
            for i, candidate in enumerate(all_candidates[30:35]):
                print(f"  {i+1}. Velocity: {candidate['velocity']:.0f}, Buying signals: {candidate['buying_signals']}, r/{candidate['subreddit']}")


if __name__ == "__main__":
    print("Script starting...", flush=True)
    print("Creating detector instance...", flush=True)
    detector = RedditTrendDetector()
    print("Starting scan...", flush=True)
    detector.scan()
