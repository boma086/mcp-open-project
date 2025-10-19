# Dockerfile for OpenProject MCP Server
# Based on Smithery.ai official recommendations

# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-alpine

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r requirements.txt

# Then, add the rest of the project source code
COPY . /app

# Place executables in the environment at the front of the path
ENV PATH="/root/.local/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

# Set default port (Smithery will override this to 8081)
ENV PORT=8081

# Run the application directly using Python
CMD ["python", "-m", "openproject.server"]