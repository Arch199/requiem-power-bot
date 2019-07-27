import praw

BOT_NAME = 'RequiemPowerBot'
REPLY_MESSAGE = 'This is... the power of [Requiem](https://youtu.be/qs3t2pE4ZsE)'
MIN_CHAIN_LEN = 3

reddit = praw.Reddit(BOT_NAME)

# Look for chains among strings of comments everywhere
while True:
    for comment in reddit.subreddit('all').stream.comments():
        summary = comment.body[:100].replace('\n', '')
        print(f'Looking at r/{comment.subreddit} comment: "{summary}..."')

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
            original_comment.reply(REPLY_MESSAGE)
            print(f'--- !!! Replied to comment! !!! ---\n')
