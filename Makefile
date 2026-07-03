# Build and start the bot in the background
up:
	docker compose up -d --build

# Stop the bot
down:
	docker compose down

# Build only, don't start
build:
	docker compose build

# Restart (down then up)
restart: down up

# Tail live logs
logs:
	docker compose logs -f

# Check status
ps:
	docker compose ps

# Stop and remove everything, including unused images (careful — frees disk space)
clean:
	docker compose down --rmi all

.PHONY: up down build restart logs ps clean

