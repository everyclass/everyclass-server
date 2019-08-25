import os

import gc
from ddtrace import patch_all, tracer

from everyclass.server import create_app

patch_all()
if os.environ.get("DD_AGENT_HOST", None) and os.environ.get("DD_TRACE_AGENT_PORT", None):
    tracer.configure(hostname=os.environ['DD_AGENT_HOST'],
                     port=os.environ['DD_TRACE_AGENT_PORT'])
else:
    print("WARNING: or DD_TRACE_AGENT_PORT not set, ignore configuring datadog tracer.")

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
