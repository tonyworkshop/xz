uv run ./src/fetch_topics.py --update 30 --debug
uv run ./src/import_data.py
uv run ./src/download_resources.py --articles --debug
uv run ./src/download_resources.py --images --debug