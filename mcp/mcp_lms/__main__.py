"""Allow running as `python -m mcp_lms [server] [args]`."""

import asyncio
import sys

if len(sys.argv) > 1 and sys.argv[1] == "observability":
    from mcp_lms.observability import main
    asyncio.run(main())
else:
    from mcp_lms.server import main
    base_url = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(main(base_url))
