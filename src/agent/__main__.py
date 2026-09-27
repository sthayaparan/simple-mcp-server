"""Run the console agent: python -m agent."""

import asyncio
import contextlib

from agent.main import main

with contextlib.suppress(KeyboardInterrupt):
    asyncio.run(main())
