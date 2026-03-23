.PHONY: up down build logs restart ps

up:
	docker compose up -d --build

down:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f

restart:
	$(MAKE) down
	$(MAKE) up

ps:
	docker compose ps
