import os
import time
from datetime import datetime, timezone, timedelta
import praw #Reddit API
import prawcore.exceptions
from fluent import sender
from dotenv import load_dotenv

# Load environment variables from .env file 
load_dotenv()

# Configuration variables 
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")
FLUENTD_HOST = os.getenv("FLUENTD_HOST")
FLUENTD_PORT = int(os.getenv("FLUENTD_PORT"))

# List of subreddits to monitor 
SUBREDDITS = [
    "techjobs", "programmingjobs", "sysadminjobs",
    "devopsjobs", "webdevjobs"
]

# Manage api
PAUSE_EVERY = 100               # Pause every x posts (avoid api rate limit)
SLEEP_TIME = 2                  # Pauses duration
DAYS_BACK = 356                 # Ignore posts older than a year
SEEN_IDS_FILE = "sent_post_ids.txt"  # Track posts already sent

# Keywords to identify job postings
KEYWORDS = [
    'hire', 'hiring', 'for hire', 'job opening',
    'position available', 'looking for', 'contract',
    'freelance'
]

# Reddit API Client credentials
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

# Set up Fluentd 
FLUENT_TAG = "reddit.jobs"
FLUENT_HOST = os.getenv("FLUENTD_HOST", "fluentd")
FLUENT_PORT = int(os.getenv("FLUENTD_PORT", "24224"))

fluentd_logger = sender.FluentSender(FLUENT_TAG, host=FLUENT_HOST, port=FLUENT_PORT)

# Load already sent posts
if os.path.exists(SEEN_IDS_FILE):
    with open(SEEN_IDS_FILE, "r") as f:
        sent_ids = set(line.strip() for line in f)
else:
    sent_ids = set()

# Save id when a post is sent
def save_sent_id(post_id):
    with open(SEEN_IDS_FILE, "a") as f:
        f.write(post_id + "\n")

# Check if reddit post contains "job posting" keywords
def is_relevant(post):
    text = f"{post.title} {post.selftext}".lower()
    return any(keyword in text for keyword in KEYWORDS)

# Fetch new posts from a subreddit
def fetch_posts_from_subreddit(subreddit_name, limit):
    print(f"→ Reading from r/{subreddit_name}")
    try:
        subreddit = reddit.subreddit(subreddit_name)
        return subreddit.new(limit=limit)
    except Exception as e:
        print(f"⚠️ Error while accessing r/{subreddit_name}: {e}")
        return []

# Filter single posts
def process_post(post, subreddit_name):
    try:
        created_dt = datetime.fromtimestamp(post.created_utc, timezone.utc)

        # Skip old posts
        if created_dt < datetime.now(timezone.utc) - timedelta(days=DAYS_BACK):
            return None

        # Skip if post was already sent
        if post.id in sent_ids:
            return None

        # Skip if not job-related
        if not is_relevant(post):
            return None

        # Return cleaned post data
        return {
            "id": post.id,
            "title": post.title,
            "created_utc": created_dt.isoformat(),
            "selftext": post.selftext[:5000],
            "subreddit": subreddit_name,
            "url": post.url
        }

    # Specific error to notify when a post is no longer available (deleted or private)
    except prawcore.exceptions.NotFound:
        print(f"Post {post.id} not found (404).")

    except Exception as e:
        print(f"Error while processing post {getattr(post, 'id', '?')}: {e}")
    return None

# Main function
def run_pipeline(limit):
    total_sent = 0

    for subreddit_name in SUBREDDITS:
        posts = fetch_posts_from_subreddit(subreddit_name, limit)

        for i, post in enumerate(posts, 1):
            result = process_post(post, subreddit_name)
            if result:
                try:
                    fluentd_logger.emit("post", result)
                    print(f"Sent post {result['id']} | {result['title'][:60]}")
                    sent_ids.add(result["id"])
                    save_sent_id(result["id"])
                    total_sent += 1
                except Exception as e:
                    print(f"Failed to send post {result['id']} to Fluentd: {e}")

            # Pause to avoid reddit api rate limit
            if i % PAUSE_EVERY == 0:
                print(f"⏸ Pausing for {SLEEP_TIME} seconds to avoid rate limits...")
                time.sleep(SLEEP_TIME)

        print(f"✔️ Finished r/{subreddit_name} — Sleeping 5 seconds before next subreddit...")
        time.sleep(5)

    fluentd_logger.close()
    print(f"🏁 Pipeline complete. Total posts sent: {total_sent}")

# Loop
if __name__ == "__main__":
    print("🚀 Starting continuous Reddit scraping pipeline")

    first_run = True

    while True:
        try:
            # On the first run, fetch a larger number of posts. 
            # On subsequent runs, reduce the limit since older posts have already been processed.
            if first_run:
                limit = 2000
                first_run = False
            else:
                limit = 50

            run_pipeline(limit)

            # Wait before the next loop
            print("⏳ Waiting 60 seconds before next run...\n")
            time.sleep(60)

        except Exception as e:
            print(f"❌ Error during pipeline execution: {e}")
            print("🔁 Retrying in 60 seconds...")
            time.sleep(60)
