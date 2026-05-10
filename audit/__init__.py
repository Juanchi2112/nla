"""Audit module: pre-deployment policy compliance auditor for open-source LLMs.

Loads .env on import so the CLI scripts (audit.generator, audit.run) get
ANTHROPIC_API_KEY without each one having to remember to call load_dotenv.
"""

from dotenv import load_dotenv

load_dotenv()
