import faulthandler
import gc
import threading

from everyclass.server import create_app

# disable gc and freeze
gc.set_threshold(0)  # 700, 10, 10 as default
gc.freeze()

# dump faults
faulthandler.enable()

# enlarge alpine linux stack size
threading.stack_size(2 * 1024 * 1024)

app = create_app()


@app.cli.command()
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


if __name__ == '__main__':
    app = create_app(outside_container=True)
    app.run()
