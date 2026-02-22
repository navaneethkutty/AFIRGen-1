FROM python:3.11.9-slim as base

ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Create a non-privileged user that the app will run under.
# See https://docs.docker.com/go/dockerfile-user-best-practices/
# ARG UID=10001
# RUN adduser \
#     --disabled-password \
#     --gecos "" \
#     --home "/nonexistent" \
#     --shell "/sbin/nologin" \
#     --no-create-home \
#     --uid "${UID}" \
#     appuser


RUN apt-get update && apt-get install -y \
    build-essential \
    libsndfile1 \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
# RUN --mount=type=cache,target=/root/.cache/pip \
#     --mount=type=bind,source=requirements.txt,target=requirements.txt \
#     python -m pip install -r requirements.txt


COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


# Copy the backend source code into the container.
# NOTE: agentv5 imports local packages (infrastructure/, services/, middleware/, etc.).
# Copying only agentv5.py causes runtime import failures in production.
COPY . .
# Expose the port that the application listens on.
EXPOSE 8000

# Run the application.
CMD uvicorn 'agentv5:app' --host=0.0.0.0 --port=8000
