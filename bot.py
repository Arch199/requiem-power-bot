import threading

import praw

BOT_NAME = 'RequiemPowerBot'
REPLY_MESSAGE = 'This is... the power of [Requiem](https://youtu.be/qs3t2pE4ZsE?t=100).'
MIN_CHAIN_LEN = 3

reddit = praw.Reddit(BOT_NAME)


# Main feature: automatically breaking comment chains
def chain_break_loop():
    # Look for chains among strings of comments everywhere
    while True:
        for comment in reddit.subreddit('all').stream.comments():
            summary = comment.body[:50].replace('\n', ' ')
            if len(comment.body) > 50:
                summary += '...'
            print(f'Looking at r/{comment.subreddit} comment: "{summary}"')

            # Check if the comment and its parents form a chain
            original_comment = comment
            is_chain = True
            chain_len = 1
            while chain_len < MIN_CHAIN_LEN:
                parent = comment.parent()
                if type(parent) != praw.models.Comment or parent.body != comment.body:
                    is_chain = False
                    break
                chain_len += 1
                comment = parent

            # Reply and break the chain if found
            if is_chain:
                reply_with_meme(original_comment)


# Secondary feature: respond to summons
def summon_response_loop():
    while True:
        # from: https://github.com/praw-dev/praw/issues/749
        for m in reddit.inbox.mentions():
            if m.new:
                print(f'Summoned by user {m.author}!')
                comment = reddit.comment(m.id)
                reply_with_meme(comment)
                m.mark_read()


# Reply function
def reply_with_meme(comment):
    comment.reply(REPLY_MESSAGE)
    print(f'--- !!! Replied to comment! !!! ---')


if __name__ == '__main__':
    # Give the secondary summon response feature to a daemon thread
    threading.Thread(target=summon_response_loop, daemon=True).start()

    # Set the main thread to work on looking to break comment chains
    chain_break_loop()
