#!/usr/bin/env python
import os
from everyclass import celery, create_app

app = create_app()
app.app_context().push()
