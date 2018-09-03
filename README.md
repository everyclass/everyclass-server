# EveryClass-server

![status](https://img.shields.io/badge/status-stable-green.svg)
![python version](https://img.shields.io/badge/python-3.6-blue.svg)
![license](https://img.shields.io/badge/license-MPL_2.0-orange.svg)
[![Build Status](https://travis-ci.org/fr0der1c/EveryClass-server.svg?branch=develop)](https://travis-ci.org/fr0der1c/EveryClass-server)
![works-on](https://img.shields.io/badge/works%20on-my%20computer-brightgreen.svg)
[![code-coverage](https://codecov.io/gh/fr0der1c/EveryClass-server/branch/master/graph/badge.svg)](https://codecov.io/gh/fr0der1c/EveryClass-server)

This is the web server part of [EveryClass](https://github.com/fr0der1c/EveryClass) project.


### Communication

If you found any problem of the code, please open an issue here and make sure you provided much information.

To discuss questions regarding the project, I suggest you join our [forum](https://base.admirable.one/c/everyclass) (Chinese).


### Technology stack

- uWSGI: the gateway between programme itself and Nginx reverse proxy
- Flask: the micro Python web framework
- MySQL: database


### Using the source

1. Set a Python 3.6.0 virtualenv, and install required packages in ``requirements.txt``
2. Copy `everyclass/config/default.py`. Rename it `development.py` and change some settings for local development
3. Import database. Structure can be found [here](https://github.com/fr0der1c/EveryClass-collector/tree/master/sql), but you need to dummy some content yourself.
4. set the environment variable `MODE` to `DEVELOPMENT`, then run `ec_server.py`

### Contributions, Bug Reports, Feature Requests

This is an open source project and we would be happy to see contributors who report bugs and file feature requests submitting pull requests as well. Please report issues here [https://github.com/fr0der1c/EveryClass-server/issues](https://github.com/fr0der1c/EveryClass-server/issues)

### Branch Policy

Please get familiar with **git-flow** before you start contributing. It's a work flow to make source code better to manage.

We have the following branches :
- **development**: All development goes on in this branch. If you're making a contribution, please make a pull request to development. PRs to must pass a build check and a unit-test check on Travis.
- **master**: This is the actual code running on the [server](https://every.admirable.one). After significant features/bug-fixes are accumulated on development, we make a version update, and make a release.


### Contributions Best Practices
#### Commits

- Write clear meaningful git commit messages
- Make sure your PR's description contains GitHub's special keyword references that automatically close the related issue when the PR is merged. (More info at  [https://github.com/blog/1506-closing-issues-via-pull-requests](https://github.com/blog/1506-closing-issues-via-pull-requests))
- When you make very very minor changes to a PR of yours (like for example fixing a failing travis build or some small style corrections or minor changes requested by reviewers) make sure you squash your commits afterwards so that you don't have an absurd number of commits for a very small fix. (Learn how to squash at https://davidwalsh.name/squash-commits-git )


#### Feature Requests and Bug Reports

When you file a feature request or when you are submitting a bug report to the issue tracker, make sure you add steps to reproduce it. Especially if that bug is some weird/rare one.

#### Join the development

Feel free to join the development and happy coding. Again, please get familiar with **git-flow** before you start contributing.