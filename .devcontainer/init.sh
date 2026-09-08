#!/bin/bash
set -e

echo "🚀 Setting up SpecterDefence development environment..."

# Update system packages
apt-get update
apt-get upgrade -y
apt-get install -y --no-install-recommends \
    build-essential \
    postgresql-client \
    redis-tools

# Install Poetry
python3 -m pip install --upgrade pip setuptools wheel
pip install poetry==1.8.3

# Install Python dependencies
echo "📦 Installing Python dependencies..."
poetry install

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
poetry run pre-commit install || true

# Install Node dependencies
echo "📦 Installing Node dependencies..."
cd frontend
npm ci
cd ..

# Generate secrets if needed
if [ ! -f ".env.local" ]; then
    echo "🔐 Generating local environment file..."
    python3 << 'EOF'
import secrets
import os
from pathlib import Path

env_file = Path(".env.local")
if not env_file.exists():
    with open(env_file, "w") as f:
        f.write("# Local development environment\n")
        f.write("DEBUG=1\n")
        f.write("TESTING=false\n")
        f.write(f"SECRET_KEY={secrets.token_hex(32)}\n")
        f.write(f"JWT_SECRET_KEY={secrets.token_hex(32)}\n")
        f.write("DATABASE_URL=sqlite:///./specterdefence.db\n")
        f.write("# Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n")
        f.write(f"ENCRYPTION_KEY={secrets.token_urlsafe(32)}\n")
        f.write(f"ENCRYPTION_SALT={secrets.token_hex(16)}\n")
    print(f"✅ Created .env.local - update ENCRYPTION_KEY and ENCRYPTION_SALT")
    os.chmod(env_file, 0o600)
EOF
fi

echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Update .env.local with required configuration"
echo "  2. Start services: docker-compose up -d"
echo "  3. Run backend: make run"
echo "  4. Run frontend: cd frontend && npm run dev"
