import json
import logging
import os
import time
import threading

import praw

logging.basicConfig(level=logging.INFO, format='[{threadName}] {message}', style='{')
logger = logging.getLogger()

BOT_NAME = 'RequiemPowerBot'
REPLY_MESSAGE = 'This is... the power of [Requiem](https://youtu.be/qs3t2pE4ZsE?t=100).'
CHAIN_LEN = 3
COMMENT_SUMMARY_LEN = 50
DEFAULT_TARGET_SUBS = ('ShitPostCrusaders', 'Animemes', 'animememes')
MULTIREDDITS = ('target_subs', 'ignored_subs')
MAX_TARGETS = 100
EXPAND_INTERVAL = 60 * 60 * 24  # 1 day in seconds
PRUNE_INTERVAL = 60 * 10  # 10 minutes in seconds


class RequiemPowerBot:
    """ The main class behind the bot's functionality. """

    def __init__(self):
        """ Loads any cached data and starts the features on separate threads. """

        self.reddit = praw.Reddit(BOT_NAME)

        # Load multireddit data
        for multi in MULTIREDDITS:
            setattr(self, multi, self.reddit.multireddit(BOT_NAME, multi))

        # Give the summon response and experimentation features to daemon threads
        for f in (self.respond_to_summons, self.expand_target_subs, self.prune_target_subs):
            threading.Thread(target=f, daemon=True, name='Thread-' + f.__name__).start()

        # Set the main thread to work on looking to break comment chains
        self.break_chains()

    def break_chains(self):
        """ Search for comment chains `CHAIN_LEN` in length containing all the same comment. """

        for comment in self.target_subs.stream.comments():
            summary = comment.body[:COMMENT_SUMMARY_LEN].replace('\n', ' ')
            if len(comment.body) > COMMENT_SUMMARY_LEN:
                summary += '...'
            logger.info(f'Looking at r/{comment.subreddit} comment: "{summary}"')

            # Check if the comment and its parents form a chain
            original_comment = comment
            is_chain = True
            chain_len = 1
            while chain_len < CHAIN_LEN:
                parent = comment.parent()
                if not isinstance(parent, praw.models.Comment) or parent.body != comment.body:
                    is_chain = False
                    break
                chain_len += 1
                comment = parent

            # Reply and break the chain if found, ensuring it is exactly the right length
            parent = comment.parent()
            if is_chain and (isinstance(parent, praw.models.Submission) or parent.body != original_comment.body):
                self.reply_with_meme(original_comment)

    def respond_to_summons(self):
        """ Respond to summons (username mentions). """

        # from: https://github.com/praw-dev/praw/issues/749
        while True:
            for msg in self.reddit.inbox.mentions():
                if msg.new:
                    logger.info(f'Summoned by user {msg.author}!')
                    comment = self.reddit.comment(msg.id)
                    self.reply_with_meme(comment)
                    msg.mark_read()

    def expand_target_subs(self):
        """ Occasionally attempt to expand to a new target sub. """

        while True:
            logger.info('Trying to expand target subs')
            # Try out a random sub that we haven't ignored or been banned from
            while True:
                new_sub = self.reddit.random_subreddit()
                logger.info(f'Got random sub: {new_sub}')
                if not new_sub.user_is_banned and new_sub not in self.ignored_subs.subreddits:
                    break
            logger.info(f'Success! Adding {new_sub} to targets')
            self.target_subs.add(new_sub)

            time.sleep(EXPAND_INTERVAL)

    def prune_target_subs(self):
        """ Ignore subs where we have low comment karma. """

        while True:
            # Set a lower karma bound based on how many targets we have
            if len(self.target_subs.subreddits) > MAX_TARGETS / 2:
                min_karma = 2
            else:
                min_karma = 1

            # Check for target subs we should ignore
            karma_dict = self.reddit.user.karma()
            for sub in self.target_subs.subreddits:
                # Remove subreddit's we're banned from
                if sub.user_is_banned:
                    self.target_subs.remove(sub)
                # Ignore subs we have low karma in
                elif sub in karma_dict and karma_dict[sub]['comment_karma'] < min_karma:
                    logger.info(f'Ignoring {sub}')
                    if len(self.ignored_subs.subreddits) >= MAX_TARGETS:
                        logger.info('Too many ignored subs: resetting')
                        self.ignored_subs.update(subreddits=[])
                    self.target_subs.remove(sub)
                    self.ignored_subs.add(sub)

            time.sleep(PRUNE_INTERVAL)

    @staticmethod
    def reply_with_meme(comment):
        """ Reply to a comment, ensuring it isn't ours to avoid an infinite loop. """

        if comment.author != BOT_NAME:
            comment.reply(REPLY_MESSAGE)
            logger.info(f'--- !!! Replied to comment! !!! ---')


if __name__ == '__main__':
    RequiemPowerBot()
