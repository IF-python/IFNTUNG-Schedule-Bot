run-dev:
	sh -c "docker-compose up"

run-prod:
	sh -c "docker-compose up -d"

build:
	sh -c "docker-compose build"

down:
    sh -c "docker-compose down"

deploy:
	make down
    make build
	make run-prod

logs:
    sh -c "docker logs -f schedule-bot"
