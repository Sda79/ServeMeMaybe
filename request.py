"""Request Module"""
import asyncio
from typing import List, Self, Tuple
from headers import Headers

ERROR_MALFORMED_REQUEST_LINE = ValueError("Malformed request line")
ERROR_UNSUPPORTED_HTTP_VERSION = NotImplementedError("HTTP version 1.1 supported only")
ERROR_MALFORMED_REQUEST = ValueError("Malformed request")

# Request Class states
RQ_STATE_INIT = 0
RQ_STATE_HEADER = 1
RQ_STATE_BODY = 2
RQ_STATE_DONE = 3

RQ_PARSER_READ_TIMEOUT = 0.25
RQ_READ_CHUNK_SIZE = 1500

class RequestLine:
    """Request line of a request
        - Method
        - Target
        - Version
    """
    def __init__(self, http_version: str, request_target: str, method: str):
        self.http_version = http_version
        self.request_target = request_target
        self.method = method

    def __str__(self) -> str:
        return f"""Request line:
- Method: {self.method} 
- Target: {self.request_target}
- Version: {self.http_version}
"""

    @classmethod
    def parse_request_line(cls: type[Self], request: str) -> Tuple[int, "RequestLine" ]:
        """Class method to build a Request line from a string"""

        # split the string with CRLF
        lines = request.split("\r\n")

        # if the string doesn't contain CRLF
        if len(lines) <= 1:
            return 0, None

        first_line = lines[0]

        parts: List[str] = first_line.split()

        # not enough parts
        if len(parts) != 3:
            raise ERROR_MALFORMED_REQUEST_LINE

        http_version = parts.pop()
        request_target = parts.pop()
        method = parts.pop()

        if method.upper() != method:
            raise ERROR_MALFORMED_REQUEST_LINE

        try:
            # http version syntax
            http_version = http_version.split("/").pop()
        except IndexError as e:
            raise ERROR_MALFORMED_REQUEST_LINE from e

        if http_version != "1.1":
            raise ERROR_UNSUPPORTED_HTTP_VERSION

        return len(first_line) + len("\r\n"), cls(http_version, request_target, method)

class Request:
    """Request 
        - .parsing state :
            - RQ_STATE_INIT -> init
            - RQ_STATE_HEADER -> parsing headers
            - RQ_STATE_BODY -> parsing body
            - RQ_STATE_DONE -> done
        - Request line
        - Headers
        - Body
    """
    def __init__(self, state: int, request_line: RequestLine, headers: Headers, body: bytes):
        self.state = state # 0 -> initialized, 1 -> parsing headers, 2 -> parsing body 3 -> done
        self.request_line = request_line
        self.headers = headers
        self.body = body

    def __str__(self) -> str:
        return f"{self.request_line}{self.headers}Body:\n{self.body.decode()}"

    @classmethod
    async def request_from_reader(cls: type[Self], reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> "Request":
        """Class method to build a Request object from a stream"""
        buf: bytes = b""
        start = 0
        request = cls(RQ_STATE_INIT, RequestLine("", "", ""), Headers(), b"")

        # Parse until done state
        while request.state != RQ_STATE_DONE:

            # Timeout if no read with 250ms close connection and raise malformed request error
            try:
                buf += await asyncio.wait_for(
                    reader.read(RQ_READ_CHUNK_SIZE),
                    timeout=RQ_PARSER_READ_TIMEOUT
                )
            except asyncio.TimeoutError as e:
                writer.close()
                await writer.wait_closed()
                raise ERROR_MALFORMED_REQUEST from e

            # Try to parse the whole buffer
            while True:
                start = request.parse(buf)
                buf = buf[start:]
                if start == 0:
                    break

            # If connection closed and state is parsing headers raise error
            if reader.at_eof() and request.state < RQ_STATE_BODY:
                writer.close()
                await writer.wait_closed()
                raise ERROR_MALFORMED_REQUEST

        print(request)
        return request

    def parse(self, data: bytes) -> int:
        """Method that update the request object from new data"""
        if self.state == RQ_STATE_INIT:
            # parsing request line
            count, request_line = RequestLine.parse_request_line(data.decode())
            if count != 0:
                self.request_line = request_line
                self.state = RQ_STATE_HEADER
            return count
        elif self.state == RQ_STATE_HEADER:
            # parsing headers
            count, done = self.headers.parse(data)
            if done:
                self.state = RQ_STATE_BODY
            return count
        elif self.state == RQ_STATE_BODY:
            # parsing body
            try:
                content_length = self.headers.get("Content-Length")
                content_length = int(content_length)
                self.body += data
                if len(self.body) > content_length:
                    raise ValueError("malformed request")
                elif len(self.body) == content_length:
                    self.state = 3
                return len(data)
            except KeyError:
                self.state = 3
                return 0
        else:
            return 0
