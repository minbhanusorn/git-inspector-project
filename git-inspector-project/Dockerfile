FROM python:3.13-slim

WORKDIR /app

RUN pip install click rich colorama

COPY . .

ENTRYPOINT ["python", "-m", "git_inspector.cli"]
