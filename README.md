# EveryClass-server

![status](https://img.shields.io/badge/status-stable-green.svg)
![python version](https://img.shields.io/badge/python-3.7-blue.svg)
![license](https://img.shields.io/badge/license-MPL_2.0-orange.svg)
[![Build Status](https://travis-ci.org/fr0der1c/EveryClass-server.svg?branch=develop)](https://travis-ci.org/fr0der1c/EveryClass-server)
![works-on](https://img.shields.io/badge/works%20on-my%20computer-brightgreen.svg)
[![code-coverage](https://codecov.io/gh/fr0der1c/EveryClass-server/branch/master/graph/badge.svg)](https://codecov.io/gh/fr0der1c/EveryClass-server)

This is the web server part of [EveryClass](https://github.com/fr0der1c/EveryClass) project.


### Communication

If you found any problem of the code, please open an issue here and make sure you provided much information.

To discuss questions regarding the project, I suggest you join our [forum](https://base.admirable.pro/c/everyclass) (Chinese).


### Technology stack

- uWSGI: the gateway between programme itself and Nginx reverse proxy
- Flask: the micro Python web framework
- MongoDB: database


### Using the source

1. Use ``pipenv sync`` to build a virtualenv with dependencies installed
2. Copy `everyclass/api_server/config/default.py` and name it `development.py`. Change settings to adjust to your local development environment
4. Set the environment variable `MODE` to `DEVELOPMENT`, then run `server.py`

### Contributions, Bug Reports, Feature Requests

This is an open source project and we would be happy to see contributors who report bugs and file feature requests submitting pull requests as well. Please report issues here [https://github.com/fr0der1c/EveryClass-server/issues](https://github.com/fr0der1c/EveryClass-server/issues)

### Branch Policy

- All your development goes on **feature/feature-name** branch. When you are done, make a pull request or just merge to `master` branch if you have permission
- Tagged commits following the pattern `vX.X.X` will be watched by Travis, our continuous integration tool, which runs unit-test check, builds Docker image, pushes the image to our private registry and updates services in `staging` environment. Tags following the pattern `vX.X.X_testing` will upgrade the `testing` environment.
- Commits should be tested in staging environment first before they are deployed to production environment.


### Contributions Best Practices
#### Commits

- Write clear meaningful git commit messages
- Make sure your PR's description contains GitHub's special keyword references that automatically close the related issue when the PR is merged. (More info at  [https://github.com/blog/1506-closing-issues-via-pull-requests](https://github.com/blog/1506-closing-issues-via-pull-requests))
- When you make very very minor changes to a PR of yours (like for example fixing a failing travis build or some small style corrections or minor changes requested by reviewers) make sure you squash your commits afterwards so that you don't have an absurd number of commits for a very small fix. (Learn how to squash at https://davidwalsh.name/squash-commits-git )


#### Feature Requests and Bug Reports

When you file a feature request or when you are submitting a bug report to the issue tracker, make sure you add steps to reproduce it. Especially if that bug is some weird/rare one.

#### Join the development

Feel free to join the development and happy coding. Again, please get familiar with **git-flow** before you start contributing.