import logging
import threading

import praw

logging.basicConfig(level=logging.INFO, format='[{threadName}] {message}', style='{')
logger = logging.getLogger()

BOT_NAME = 'RequiemPowerBot'
REPLY_MESSAGE = 'This is... the power of [Requiem](https://youtu.be/qs3t2pE4ZsE?t=122).'
SPOILER_SAFE_MESSAGE = 'This is... the power of ^(*a JoJo Part 5 spoiler*) >![Requiem](https://youtu.be/qs3t2pE4ZsE?t=122)!<.'
CHAIN_LEN = 5
COMMENT_SUMMARY_LEN = 50
TARGET_SUBS = ('ShitPostCrusaders', 'Animemes', 'animememes')


class RequiemPowerBot:
    """ The main class behind the bot's functionality. """

    def __init__(self):
        """ Loads any cached data and starts the features on separate threads. """

        self.reddit = praw.Reddit(BOT_NAME)
        self.target_subs = self.reddit.subreddit('+'.join(TARGET_SUBS))

        # Give the summon response feature to a daemon thread
        threading.Thread(target=self.respond_to_summons, daemon=True, name='Thread-summons').start()

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

    @staticmethod
    def reply_with_meme(comment):
        """ Reply to a comment, ensuring it isn't ours to avoid an infinite loop. """

        if comment.author != BOT_NAME:
            if comment.subreddit.display_name == 'Animemes':
                msg = SPOILER_SAFE_MESSAGE
            else:
                msg = REPLY_MESSAGE
            comment.reply(msg)
            logger.info(f'--- !!! Replied to comment! !!! ---')


if __name__ == '__main__':
    RequiemPowerBot()
