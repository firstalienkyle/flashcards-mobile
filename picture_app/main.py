import sys
import os

_app_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _app_dir)

# Samsung Galaxy A34 preview window — must happen before any kivy import
if not os.environ.get('ANDROID_ARGUMENT'):
    from kivy.config import Config
    Config.set('graphics', 'width',  '393')
    Config.set('graphics', 'height', '876')
    Config.set('graphics', 'resizable', '0')

import data.database as db
from ui.app import PictureApp


def main():
    db.init_db()
    PictureApp().run()


if __name__ == '__main__':
    main()
