#!/usr/bin/env python3
import os
from app.config import settings

print(f"Environment GOOGLE_API_KEY: {os.environ.get('GOOGLE_API_KEY', 'NOT SET')[:50]}...")
print(f"Settings googleApiKey: {settings.googleApiKey[:50] if settings.googleApiKey else 'EMPTY'}...")
print(f"Is configured: {bool(settings.googleApiKey)}")
