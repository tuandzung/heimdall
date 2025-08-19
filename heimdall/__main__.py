from __future__ import annotations

import asyncio

import uvicorn


def main() -> None:
    # Ensure an event loop exists on some platforms
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    uvicorn.run("heimdall.api:app", host="0.0.0.0", port=8088, reload=False)


if __name__ == "__main__":
    main()
