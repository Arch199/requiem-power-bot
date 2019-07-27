import logging
import threading

import praw

BOT_NAME = 'RequiemPowerBot'
REPLY_MESSAGE = 'This is... the power of [Requiem](https://youtu.be/qs3t2pE4ZsE?t=100).'
MIN_CHAIN_LEN = 3
COMMENT_SUMMARY_LEN = 50
SUBREDDIT = 'ShitPostCrusaders+Animemes+Anime+StardustCrusaders+Animememes'

logging.basicConfig(level=logging.INFO, format='[{asctime}] {message}', style='{')
logger = logging.getLogger()

reddit = praw.Reddit(BOT_NAME)


# Main feature: automatically breaking comment chains
def chain_break_loop():
    # Look for chains among strings of comments everywhere
    while True:
        for comment in reddit.subreddit(SUBREDDIT).stream.comments():
            summary = comment.body[:COMMENT_SUMMARY_LEN].replace('\n', ' ')
            if len(comment.body) > COMMENT_SUMMARY_LEN:
                summary += '...'
            logger.info(f'Looking at r/{comment.subreddit} comment: "{summary}"')

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
                logger.info(f'Summoned by user {m.author}!')
                comment = reddit.comment(m.id)
                reply_with_meme(comment)
                m.mark_read()


# Reply function
def reply_with_meme(comment):
    # Make sure we don't reply to ourselves and loop forever
    if comment.author != BOT_NAME:
        comment.reply(REPLY_MESSAGE)
        logger.info(f'--- !!! Replied to comment! !!! ---')


if __name__ == '__main__':
    # Give the secondary summon response feature to a daemon thread
    threading.Thread(target=summon_response_loop, daemon=True).start()

    # Set the main thread to work on looking to break comment chains
    chain_break_loop()
