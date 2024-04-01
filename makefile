DOCKER_DEV_COMPOSE_FILE := docker-compose.yml


help:  ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

build-image: ## Build docker image
	@ ${INFO} "Building required docker images"
	@ docker compose -f $(DOCKER_DEV_COMPOSE_FILE) build database-api
	@ ${INFO} "Image succesfully built"
	@ echo " "

start:build-image ## Start development server
	@ ${INFO} "starting local development server"
	@ docker compose -f $(DOCKER_DEV_COMPOSE_FILE) up

connect-to-container:build-image ## Connect to a container
	@ ${INFO} "Connecting to a container"
	@ docker compose -f $(DOCKER_DEV_COMPOSE_FILE) exec database-api /bin/bash

psql-connect: ## Connect to the database
	@ ${INFO} "Connecting to the database"
	@ docker compose -f $(DOCKER_DEV_COMPOSE_FILE) exec database_db /bin/bash -c "psql --user postgres --dbname cranecloud_db"

migrate: ## Run database migrations
	@ ${INFO} "Running database migrations"
	@ docker compose -f $(DOCKER_DEV_COMPOSE_FILE) exec database-api /bin/bash -c "poetry run alembic revision --autogenerate"
	@ ${INFO} "Migrations complete"

upgrade: ## Upgrade database migrations
	@ ${INFO} "Running database migrations"
	@ docker compose -f $(DOCKER_DEV_COMPOSE_FILE) exec database-api /bin/bash -c "poetry run alembic upgrade head"
	@ ${INFO} "Migrations complete"

test: ## Run tests
	@ ${INFO} "Running tests with coverage"
	@ docker compose -f $(DOCKER_DEV_COMPOSE_FILE) up -d database_db
	@ export FASTAPI_ENV=testing && coverage run --source app/ -m pytest
	@ coveralls
	@ ${INFO} "Tests complete"

clean: ## Remove all project images and volumes
	@ ${INFO} "Cleaning your local environment"
	@ ${INFO} "Note: All ephemeral volumes will be destroyed"
	@ docker compose -f $(DOCKER_DEV_COMPOSE_FILE) down --rmi all
	@ ${INFO} "Clean complete"


# set default target
.DEFAULT_GOAL := help

# colors
YELLOW := $(shell tput -Txterm setaf 3)
NC := "\e[0m"

#shell Functions
INFO := @bash -c 'printf $(YELLOW); echo "===> $$1"; printf $(NC)' SOME_VALUE