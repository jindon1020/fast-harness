.PHONY: run dev docker-build docker-run clean

PYTHONPATH := $(CURDIR)

run:
	PYTHONPATH=$(PYTHONPATH) uvicorn src.main:app --host 0.0.0.0 --port 8000

dev:
	PYTHONPATH=$(PYTHONPATH) uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker build -t fast-harness-runtime .

docker-run:
	docker run -p 8000:8000 --env-file .env fast-harness-runtime

clean:
	rm -rf __pycache__ src/**/__pycache__
