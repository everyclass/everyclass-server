from gevent import monkey

monkey.patch_all()

import gc
from everyclass.server import create_app

app = create_app()

# disable gc and freeze
gc.set_threshold(0)  # 700, 10, 10 as default
gc.freeze()


@app.cli.command()
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


if __name__ == '__main__':
    print("You should not run this file. Instead, run `uwsgi --ini deploy/uwsgi-local.ini` for consistent behaviour.")
