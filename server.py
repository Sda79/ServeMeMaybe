"""HTTP Server Module
Here is defined the HTTP Server class
"""
import asyncio
from collections.abc import Callable, Coroutine
from typing import Any
import request


def build_stream_handler(request_handler: Callable[[request.Request, asyncio.StreamWriter], None]) -> Coroutine[Any, Any, None]:
    """Build a stream handler from a user defined Coroutine or Function"""
    async def stream_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        # parse request if error close connection
        try:
            req = await request.Request.request_from_reader(reader, writer)
        except ValueError:
            print("Could not parse request")
            writer.write_eof()
            writer.close()
            await writer.wait_closed()
            return

        await request_handler(req, writer)

        writer.write_eof()
        writer.close()
        await writer.wait_closed()

    return stream_handler


class Server():
    """Server allow users to build an http server by passing a handler.
    Handler is built by the build_stream_handler function."""
    def __init__(self, port: str, handler: Coroutine[Any, Any, None]):
        self._port = port
        self._handler = handler
        self._server: asyncio.Server = None

    async def __aenter__(self):
        # start tcp server
        self._server = await asyncio.start_server(
            build_stream_handler(self._handler),
            "127.0.0.1",
            self._port
        )
        addrs = ', '.join(str(sock.getsockname()) for sock in self._server.sockets)
        print(f'Serving on {addrs}')
        await self._server.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        # close server
        await self._server.__aexit__()

    async def serve(self) -> None:
        """Serve for ever"""
        await self._server.serve_forever()
