# EveryClass-server

![status](https://img.shields.io/badge/status-stable-green.svg)
![python version](https://img.shields.io/badge/python-3.7-blue.svg)
![license](https://img.shields.io/badge/license-MPL_2.0-orange.svg)
[![Build Status](https://travis-ci.org/fr0der1c/EveryClass-server.svg?branch=develop)](https://travis-ci.org/fr0der1c/EveryClass-server)
![works-on](https://img.shields.io/badge/works%20on-my%20computer-brightgreen.svg)
[![code-coverage](https://codecov.io/gh/fr0der1c/EveryClass-server/branch/master/graph/badge.svg)](https://codecov.io/gh/fr0der1c/EveryClass-server)

This is the web server part of the [EveryClass](https://github.com/fr0der1c/EveryClass) project.


### Communication

If you find any problems with the code please open an issue and provide as much detail as possible.

If you wish to discuss the project, you can join our [forum](https://base.admirable.pro/c/everyclass) (Chinese).


### Technology stack

- uWSGI: the gateway between the program and Nginx reverse proxy
- Flask: the micro Python web framework
- MongoDB: database


### Using the source

1. Use ``pipenv sync`` to build a virtualenv with dependencies installed
2. Copy `everyclass/api_server/config/default.py` and name it `development.py`. Change settings to adjust to your local development environment
4. Set the environment variable `MODE` to `DEVELOPMENT`, then run `server.py`

### Contributions, Bug Reports, Feature Requests

This is an open source project and we would be happy to have contributors who report bugs, file feature requests and submit pull requests. Please report issues here: [https://github.com/AdmirablePro/everyclass/issues](https://github.com/AdmirablePro/everyclass/issues) (not issue tracker of this repository!)

### Branch Policy

- All development goes on the **feature/feature-name** branch. To commit a change make a pull request or merge to the `master` branch if you have permission
- Tagged commits following the pattern `vX.X.X` will be watched by Travis, our continuous integration tool, which runs unit-tests, builds the Docker image, pushes the image to our private registry and updates services in the `staging` environment. Tags following the pattern `vX.X.X_testing` will upgrade the `testing` environment.
- Commits should be tested in the staging environment before they are deployed to the production environment.


### Contributions Best Practices
#### Commits

- Write clear and meaningful git commit messages
- Make sure your pull request description contains GitHub's special keyword references that automatically close the related issue when merged. (More info at  [https://github.com/blog/1506-closing-issues-via-pull-requests](https://github.com/blog/1506-closing-issues-via-pull-requests))
- When you make minor changes to a pull request (like for example fixing a failing travis build or some small style corrections or minor changes requested by reviewers) squash your commits afterwards so that you don't have an absurd number of commits for a small fix. (Learn how to squash at https://davidwalsh.name/squash-commits-git )


#### Feature Requests and Bug Reports

When you file a feature request or submit a bug report to the issue tracker, add the necessary steps to reproduce it. This is very important for weird/rare bugs.
