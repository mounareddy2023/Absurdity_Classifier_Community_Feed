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


if __name__ == "__main__":
    manager.run()
