import json
import logging
import os
import time
import threading

import bmemcached
import praw

logging.basicConfig(level=logging.INFO, format='[{threadName}] {message}', style='{')
logger = logging.getLogger()

BOT_NAME = 'RequiemPowerBot'
REPLY_MESSAGE = 'This is... the power of [Requiem](https://youtu.be/qs3t2pE4ZsE?t=100).'
CHAIN_LEN = 3
COMMENT_SUMMARY_LEN = 50
DEFAULT_TARGET_SUBS = ('ShitPostCrusaders', 'Animemes', 'animememes')
CACHE_KEYS = ('target_subs', 'banned_subs', 'ignored_subs')
EXPERIMENT_INTERVAL = 60 * 60 * 24  # one day in seconds


class RequiemPowerBot:
    """ The main class behind the bot's functionality. """

    def __init__(self):
        """ Loads any cached data and starts the features on separate threads. """

        self.reddit = praw.Reddit(BOT_NAME)

        # Load cached data (current multireddit, banned and ignored subs)
        try:
            self.cache = ClientCache(bmemcached.Client(
                os.environ['MEMCACHEDCLOUD_SERVERS'].split(','),
                os.environ['MEMCACHEDCLOUD_USERNAME'],
                os.environ['MEMCACHEDCLOUD_PASSWORD'],
            ))
        except KeyError:
            self.cache = FileCache()
        self.target_subs = self.reddit.multireddit(BOT_NAME, 'target_subs')
        self.banned_subs = set(self.cache.get('banned_subs', []))
        self.ignored_subs = set(self.cache.get('ignored_subs', []))

        # Give the summon response and experimentation features to daemon threads
        for f in (self.respond_to_summons, self.expand_target_subs):
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
            if is_chain and comment.parent().body != original_comment.body:
                self.reply_with_meme(original_comment)

    def respond_to_summons(self):
        """ Respond to summons (username mentions). """

        # from: https://github.com/praw-dev/praw/issues/749
        # TODO: refactor to look through all messages and check for bans
        for m in self.reddit.inbox.mentions():
            if m.new:
                logger.info(f'Summoned by user {m.author}!')
                comment = self.reddit.comment(m.id)
                self.reply_with_meme(comment)
                m.mark_read()

    def expand_target_subs(self):
        """ Occasionally attempt to expand to a new target sub. """

        while True:
            # Check for target subs we should ignore
            karma_dict = self.reddit.user.karma()
            for sub in self.target_subs.subreddits:
                # Ignore a subreddit if we have non-positive comment karma
                if sub in karma_dict and karma_dict[sub]['comment_karma'] < 1:
                    self.target_subs.remove(sub)
                    self.ignored_subs.add(sub.display_name)

            logger.info('Trying to expand target subs')
            # Try out a random sub that we haven't ignored or been banned from
            while True:
                new_sub = self.reddit.random_subreddit()
                logger.info(f'Got random sub: {new_sub.display_name}')
                if new_sub.display_name not in self.banned_subs and new_sub.display_name not in self.ignored_subs:
                    break
            logger.info(f'Success! Adding {new_sub.display_name} to targets')
            self.target_subs.add(new_sub.display_name)

            # Update our cache
            self.cache.update({
                'target_subs': [str(s) for s in self.target_subs.subreddits],
                'banned_subs': list(self.banned_subs),
                'ignored_subs': list(self.ignored_subs),
            })
            time.sleep(EXPERIMENT_INTERVAL)

    @staticmethod
    def reply_with_meme(comment):
        """ Reply to a comment, ensuring it isn't ours to avoid an infinite loop. """

        if comment.author != BOT_NAME:
            comment.reply(REPLY_MESSAGE)
            logger.info(f'--- !!! Replied to comment! !!! ---')


class ClientCache:
    """ A wrapper for `bmemcached.Client` for partial duck-typing compatibility with `dict`. """

    def __init__(self, client):
        self.client = client

    def get(self, key, default=None):
        value = json.loads(client.get(key))
        if not value:
            return default

    def update(self, new_dict):
        self.client.set_multi(new_dict)


class FileCache:
    """ A cache for local file storage. """

    FILENAME = 'cache.json'

    def __init__(self, initial=None):
        if initial is not None:
            self._write_dict(initial)

    def get(self, key, default=None):
        return self._read_dict().get(key, default)

    def update(self, new_dict):
        self._write_dict(new_dict)

    def _read_dict(self):
        try:
            with open(self.FILENAME) as f:
                return json.loads(f.read())
        except OSError:
            return {}

    def _write_dict(self, d):
        if type(d) is not dict:
            raise ValueError('Cache must be a dict')
        with open(self.FILENAME, 'w') as f:
            f.write(json.dumps(d))


if __name__ == '__main__':
    RequiemPowerBot()
