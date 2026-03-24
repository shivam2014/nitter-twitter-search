"""Camoufox-based Twitter/X scraper with anti-detection."""

import re
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List

# Check if Camoufox is available
CAMOUFOX_AVAILABLE = False
try:
    import camoufox
    CAMOUFOX_AVAILABLE = True
except ImportError:
    pass


def scrape_user_tweets_camoufox(
    username: str,
    query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_tweets: int = 100,
    mirror: str = "https://nitter.net"
) -> Dict[str, Any]:
    """
    Scrape tweets using Camoufox browser automation.
    This bypasses bot detection using camouflaged Firefox profiles.
    """
    
    if not CAMOUFOX_AVAILABLE:
        return {
            "search_metadata": {
                "query": query,
                "user": username,
                "error": "Camoufox library not installed",
                "timestamp": datetime.now().isoformat() + "Z"
            },
            "tweets": []
        }
    
    try:
        print(f"Starting Camoufox scrape for @{username}...", file=sys.stderr)
        
        # Build the URL
        from urllib.parse import quote, urlencode
        
        # Construct query with filters
        search_query = query or ""
        
        # Determine base URL path
        if username:
            base_path = f"{mirror}/{username}/search"
        else:
            base_path = f"{mirror}/search"
        
        # Build parameters
        params = {
            "f": "tweets",  # Filter for tweets only
            "q": search_query if search_query else ""
        }
        
        # Add date filters as URL parameters (not query syntax)
        if start_date:
            params["since"] = start_date
        if end_date:
            params["until"] = end_date
        
        search_url = f"{base_path}?{urlencode(params)}"
        
        print(f"URL: {search_url}", file=sys.stderr)
        
        # Launch Camoufox browser
        browser_obj = camoufox.Camoufox(headless=True)
        browser_obj.start()
        
        try:
            playwright_browser = browser_obj.browser
            
            # Create context and page
            context = playwright_browser.new_context()
            page = context.new_page()
            
            # Navigate to the page
            print(f"Navigating to {search_url}...", file=sys.stderr)
            page.goto(search_url, wait_until="domcontentloaded")
            
            # Wait for content to load
            import time
            time.sleep(5)  # Wait for JS to render
            
            # Get page content
            content = page.content()
            
            # Check if profile is private - look for specific error patterns
            # Don't just check for words anywhere in HTML (they may appear in footer/links)
            is_private = False
            
            # Check for actual error messages or private account indicators
            import re
            
            # Look for "Sorry, this page isn't available" or similar error messages
            if re.search(r'sorry[^<]*this page isn\'t available', content.lower()):
                is_private = True
            
            # Nitter shows specific message for protected accounts:
            # "This account's tweets are protected."
            # "Only confirmed followers have access to @username's tweets."
            if re.search(r'this account.*?tweets are protected|protected account', content.lower()):
                is_private = True
            
            # Check if there are NO timeline items AND the profile header exists but shows no tweets
            timeline_items = len(re.findall(r'class="timeline-item"', content))
            profile_exists = '@' + username in content or username.lower() in content.lower()
            
            if profile_exists and timeline_items == 0:
                # Profile exists but no tweets - could be private or just empty
                # Check for explicit "private" near the profile section
                profile_section_match = re.search(r'<div[^>]*class="profile-header"[^>]*>(.*?)</div>', content, re.DOTALL | re.IGNORECASE)
                if profile_section_match:
                    profile_header = profile_section_match.group(1).lower()
                    if 'private' in profile_header or 'protected' in profile_header:
                        is_private = True
            
            if is_private:
                context.close()
                playwright_browser.close()
                return {
                    "search_metadata": {
                        "query": query,
                        "user": username,
                        "private_profile": True,
                        "error": "Profile is private or unavailable",
                        "timestamp": datetime.now().isoformat() + "Z",
                        "mirror_used": mirror
                    },
                    "tweets": []
                }
            
            # Extract tweets using JavaScript
            tweets = []
            
            # Use JavaScript to extract tweet data
            tweet_script = """() => {
                const tweets = [];
                const elements = document.querySelectorAll('.timeline-item');
                
                elements.forEach(el => {
                    const textEl = el.querySelector('.tweet-body');
                    const statsEl = el.querySelector('.tweet-stats');
                    
                    if (textEl) {
                        // Get all text content and clean it up
                        let text = textEl.textContent.trim();
                        // Remove stats numbers from text (they appear at the end)
                        if (statsEl) {
                            const statsText = statsEl.textContent.trim();
                            // Remove stats numbers from the text
                            const statsRegex = new RegExp(statsText.replace(/\\s+/g, '\\\\s+'), 'g');
                            text = text.replace(statsRegex, '').trim();
                        }
                        // Remove excessive whitespace
                        text = text.replace(/\\s+/g, ' ').trim();
                        
                        if (text && text.length > 10) { // Filter out tiny elements
                            // Extract engagement metrics from stats
                            let likes = null;
                            let retweets = null;
                            let replies = null;
                            let views = null;
                            
                            if (statsEl) {
                                const statElements = statsEl.querySelectorAll('.tweet-stat');
                                statElements.forEach(stat => {
                                    const icon = stat.querySelector('.icon-container span');
                                    const numberText = stat.textContent.trim();
                                    
                                    if (icon) {
                                        const iconClass = icon.className || '';
                                        const cleanedNumber = numberText.replace(/[^0-9.]/g, '');
                                        
                                        if (iconClass.includes('icon-comment')) {
                                            replies = cleanedNumber ? parseFloat(cleanedNumber) : null;
                                        } else if (iconClass.includes('icon-retweet')) {
                                            retweets = cleanedNumber ? parseFloat(cleanedNumber) : null;
                                        } else if (iconClass.includes('icon-heart')) {
                                            likes = cleanedNumber ? parseFloat(cleanedNumber) : null;
                                        } else if (iconClass.includes('icon-views')) {
                                            views = cleanedNumber ? parseFloat(cleanedNumber) : null;
                                        }
                                    }
                                });
                            }
                            
                            tweets.push({
                                text: text,
                                date: null,
                                likes: likes,
                                replies: replies,
                                retweets: retweets,
                                views: views
                            });
                        }
                    }
                });
                
                return tweets;
            }"""
            
            try:
                tweets_data = page.evaluate(tweet_script)
                print(f"Found {len(tweets_data)} tweets via JavaScript", file=sys.stderr)
                
                # Apply query filter if needed
                if query and query.strip():
                    query_lower = query.lower()
                    filtered_tweets = [
                        t for t in tweets_data
                        if query_lower in t.get('text', '').lower()
                    ]
                    print(f"Filtered to {len(filtered_tweets)} tweets matching query", file=sys.stderr)
                    tweets_data = filtered_tweets
                
                tweets = tweets_data[:max_tweets]
                
            except Exception as e:
                print(f"JavaScript extraction error: {e}", file=sys.stderr)
                # Fallback: parse HTML manually
                tweets = parse_tweets_from_html(content, query, max_tweets)
            
            # Clean up
            page.close()
            context.close()
            playwright_browser.close()
            
            return {
                "search_metadata": {
                    "query": query,
                    "user": username,
                    "private_profile": False,
                    "timestamp": datetime.now().isoformat() + "Z",
                    "mirror_used": mirror,
                    "method": "camoufox"
                },
                "tweets": tweets
            }
            
        except Exception as e:
            # Clean up on error
            try:
                if 'playwright_browser' in locals():
                    if 'context' in locals() and hasattr(context, 'close'):
                        context.close()
                    if hasattr(playwright_browser, 'close'):
                        playwright_browser.close()
            except:
                pass
            raise e
            
    except Exception as e:
        print(f"Camoufox scrape error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {
            "search_metadata": {
                "query": query,
                "user": username,
                "error": str(e),
                "timestamp": datetime.now().isoformat() + "Z",
                "mirror_used": mirror
            },
            "tweets": []
        }


def parse_tweets_from_html(html: str, query: Optional[str], max_tweets: int) -> List[Dict[str, Any]]:
    """Fallback: Parse tweets from HTML content"""
    tweets = []
    
    # Extract tweet blocks
    tweet_blocks = re.findall(r'<div[^>]*class="[^"]*timeline-item[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL | re.IGNORECASE)
    
    print(f"Found {len(tweet_blocks)} potential tweet blocks (fallback)", file=sys.stderr)
    
    for block in tweet_blocks[:max_tweets]:
        try:
            # Extract text from tweet-body
            text_match = re.search(r'<div[^>]*class="[^"]*tweet-body[^"]*"[^>]*>(.*?)</div>', block, re.DOTALL | re.IGNORECASE)
            
            if not text_match:
                continue
            
            text = text_match.group(1)
            # Clean up: remove HTML tags and excessive whitespace
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            
            if not text or len(text) < 10:
                continue
            
            # Apply query filter
            if query and query.strip():
                if query.lower() not in text.lower():
                    continue
            
            tweets.append({
                "text": text,
                "date": None,
                "likes": None,
                "replies": None,
                "retweets": None
            })
            
        except Exception as e:
            print(f"Error processing tweet: {e}", file=sys.stderr)
            continue
    
    return tweets
