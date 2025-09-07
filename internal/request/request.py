import asyncio
from typing import List, Self, Tuple

ERROR_MALFORMED_REQUEST_LINE = ValueError("Malformed request line")
ERROR_UNSUPPORTED_HTTP_VERSION = NotImplementedError("HTTP version 1.1 supported only")
ERROR_MALFORMED_REQUEST = ValueError("Malformed request")

class RequestLine:
    def __init__(self, http_version: str, request_target: str, method: str):
        self.http_version = http_version
        self.request_target = request_target
        self.method = method

    def __str__(self) -> str:
        return f"<RequestLine http_version={self.http_version} request_target={self.request_target} method={self.method}>"

    @classmethod
    def parse_request_line(cls: type[Self], request: str) -> Tuple[int, "RequestLine" ]:
        lines = request.split("\r\n")

        if len(lines) <= 1:
            return 0, None

        first_line = lines[0]

        parts: List[str] = first_line.split()

        if len(parts) != 3:
            raise ERROR_MALFORMED_REQUEST_LINE
            
        http_version = parts.pop()
        request_target = parts.pop()
        method = parts.pop()

        if method.upper() != method:
            raise ERROR_MALFORMED_REQUEST_LINE

        try:
            http_version = http_version.split("/").pop()
        except IndexError as e:
            raise ERROR_MALFORMED_REQUEST_LINE from e

        if http_version != "1.1":
            raise ERROR_UNSUPPORTED_HTTP_VERSION
                
        return len(first_line), cls(http_version, request_target, method)

class Request:
    def __init__(self, state: int, request_line: RequestLine):
        self.state = state # 0 -> initialized, 1 -> done
        self.request_line = request_line
    
    def __str__(self) -> str:
        return f"<Request state={self.state} request_line={self.request_line}>"

    @classmethod
    async def request_from_reader(cls: type[Self], reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> "Request":
        buf: bytes = b""
        start = 0
        request = cls(0, RequestLine("", "", ""))
        while request.state == 0:
            buf += await reader.read(8)
            start += request.parse(buf)
            buf = buf[start:]
            if reader.at_eof():
                writer.close()
                await writer.wait_closed()
                raise ERROR_MALFORMED_REQUEST

        writer.close()
        await writer.wait_closed()

        print(request)
        return request

    def parse(self, data: bytes) -> int:
        count, request_line = RequestLine.parse_request_line(data.decode())
        if count == 0:
            return 0
        self.request_line = request_line
        self.state = 1
        return count


async def main():
    server = await asyncio.start_server(Request.request_from_reader, "127.0.0.1", 42069)
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')
    async with server:
        await server.serve_forever()


asyncio.run(main())