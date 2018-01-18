import os

from everyclass import create_app

app = create_app()
print('MODE: {}; Running under %s config'.format(os.environ.get('MODE'), app.config['CONFIG_NAME']))
