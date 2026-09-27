# GramDrishti demo stack (S14). Needs Docker with Compose v2. See docs/docker.md.
.PHONY: up down logs ps offline e2e fresh-check clean

up:            ## build, prepare (trains on first run) and start everything
	./scripts/demo.sh

down:          ## stop the containers (volumes with the model, snapshots and reviews are kept)
	docker compose down

logs:          ## follow the logs
	docker compose logs -f --tail=100

ps:            ## container status and health
	docker compose ps

offline:       ## export snapshot mode again (after approving advisories) for the offline copy on :8081
	docker compose run --rm prepare python -m gramdrishti.pipeline.prepare_demo \
	  --offline-out /app/offline/snapshot --refresh-offline

e2e:           ## demo walk-through (Playwright) on an isolated stack (ports 180xx), then API-down check
	./scripts/e2e_docker.sh

fresh-check:   ## clone into a temp folder, follow the README quick start, hit endpoints, clean up
	./scripts/fresh_clone_check.sh

clean:         ## stop and DELETE the volumes (model, snapshots, reviews, feedback); next up retrains
	docker compose down -v
