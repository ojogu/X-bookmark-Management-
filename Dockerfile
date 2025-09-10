FROM python:3.11-slim

# set working directory inside container
WORKDIR /app

# copy only requirements first (for caching optimization)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# copy ONLY your source code (exclude env, .git, etc. via .dockerignore)
COPY . .

# set default command (point to entry file inside src)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port","8000"]
