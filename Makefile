.PHONY: etl frontend

etl:
	cd etl && uv run python main.py

frontend:
	cd frontend && npm run dev
