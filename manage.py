import logging

from flask_apscheduler import APScheduler
from flask_script import Manager, Command

from feed.feed_service import FeedService
from app import app

manager = Manager(app)


class RunCron(Command):
    """Running Cron"""

    def run(self):
        with app.app_context():
            scheduler = APScheduler()
            scheduler.init_app(app)

            log = logging.getLogger('apscheduler.executors.default')
            log.setLevel(logging.INFO)

            fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
            h = logging.StreamHandler()
            h.setFormatter(fmt)
            log.addHandler(h)
            scheduler.start()
            app.run(debug=False, port=5001, host='0.0.0.0')


class RunCachePosts(Command):

    def run(self):
        FeedService.cache_posts()


class RunCacheArticle(Command):

    def run(self):
        pass


class RunUpdateDefaultFeed(Command):

    def run(self):
        FeedService.update_default_feed()


class RunUpdatePersonalisedFeed(Command):

    def run(self):
        FeedService.update_personalised_feed()


class RunUpdatePostPickle(Command):

    def run(self):
        FeedService.update_post_pickle()


class RunUpdateArticlePickle(Command):

    def run(self):
        FeedService.update_article_pickle()


class RunUpdateCommentPickle(Command):

    def run(self):
        FeedService.update_comment_pickle()


class RunUpdateFollowPickle(Command):

    def run(self):
        FeedService.update_follow_pickle()


class RunUpdateSharePickle(Command):

    def run(self):
        FeedService.update_share_pickle()


class RunUpdateReactionPickle(Command):

    def run(self):
        FeedService.update_reaction_pickle()


class RunUpdateMemberPickle(Command):

    def run(self):
        FeedService.update_member_pickle()


class RunUpdatePinnedPosts(Command):

    def run(self):
        FeedService.update_pinned_posts()


class RunUpdateTopicPickle(Command):

    def run(self):
        FeedService.update_topic_pickle()


class RunUpdateFeedWithNewData(Command):

    def run(self):
        FeedService.update_feed_with_new_data()


class RunUpdateActiveUserEngagement(Command):

    def run(self):
        FeedService.update_active_user_engagement()


class RunUpdateProductPickle(Command):

    def run(self):
        FeedService.update_product_pickle()


class RunUpdateBlockPickle(Command):

    def run(self):
        FeedService.update_block_pickle()


class FeedCleanUp(Command):

    def run(self):
        FeedService.feed_clean_up()


class BbcTrendingQuestion(Command):

    def run(self):
        FeedService.bbc_trending_question()


manager.add_command('cron', RunCron())
manager.add_command('cache_posts', RunCachePosts())
manager.add_command('cache_articles', RunCacheArticle())
manager.add_command('update_pinned_posts', RunUpdatePinnedPosts())
manager.add_command('update_default_feed', RunUpdateDefaultFeed())
manager.add_command('update_personalised_feed', RunUpdatePersonalisedFeed())
manager.add_command('update_post_pickle', RunUpdatePostPickle())
manager.add_command('update_article_pickle', RunUpdateArticlePickle())
manager.add_command('update_comment_pickle', RunUpdateCommentPickle())
manager.add_command('update_follow_pickle', RunUpdateFollowPickle())
manager.add_command('update_share_pickle', RunUpdateSharePickle())
manager.add_command('update_reaction_pickle', RunUpdateReactionPickle())
manager.add_command('update_member_pickle', RunUpdateMemberPickle())
manager.add_command('update_topic_pickle', RunUpdateTopicPickle())
manager.add_command('update_product_pickle', RunUpdateProductPickle())
manager.add_command('update_block_pickle', RunUpdateBlockPickle())
manager.add_command('update_feed_with_new_data', RunUpdateFeedWithNewData())
manager.add_command('update_active_user_engagement', RunUpdateActiveUserEngagement())
manager.add_command('feed_clean_up', FeedCleanUp())
manager.add_command('bbc_trending_question', BbcTrendingQuestion())

if __name__ == "__main__":
    manager.run()
