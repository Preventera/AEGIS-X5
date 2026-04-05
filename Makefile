.PHONY: up down test logs status build clean

# --- Docker Compose commands ---

up:
	docker compose up -d --build
	@echo ""
	@echo "  AEGIS-X5 is running:"
	@echo "    API:       http://localhost:4000/api/docs"
	@echo "    Dashboard: http://localhost:4005"
	@echo "    Postgres:  localhost:5432"
	@echo "    Redis:     localhost:6379"
	@echo ""

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f --tail 50

status:
	docker compose ps

# --- Development commands ---

test:
	python -m pytest tests/ -v --tb=short

test-fast:
	python -m pytest tests/ -x --tb=short -q

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

# --- Utilities ---

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

init:
	python -m aegis.cli init

dashboard:
	python -m aegis.cli dashboard
