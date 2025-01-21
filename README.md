# Database API
[![Coverage Status](https://coveralls.io/repos/github/crane-cloud/database-api/badge.svg?branch=develop)](https://coveralls.io/github/crane-cloud/database-api?branch=develop)
[![Prod](https://github.com/crane-cloud/database-api/actions/workflows/prod.yml/badge.svg)](https://github.com/crane-cloud/database-api/actions/workflows/prod.yml)
[![staging](https://github.com/crane-cloud/database-api/actions/workflows/staging.yaml/badge.svg)](https://github.com/crane-cloud/database-api/actions/workflows/staging.yaml)

The database API offers a convenient and efficient way to create MySQL and PostgreSQL databases for users on the Crane Cloud platform

# Project Setup

Follow these steps to have a local running copy of the app.

Clone The Repo

```
git clone https://github.com/crane-cloud/database-api.git
```

# Running application with Docker

`make` is a build automation tool that is used to manage the build process of a software project.

In the project directory, running `make` shows you a list of commands to use.

Run `make start` to start the application and required services.

Run `make connect-to-container` to connect to the FastAPI application container.

Run `make test` to run tests in the application
