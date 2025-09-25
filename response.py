"""Response module"""
import asyncio
from headers import Headers

code_reason_map = {
    200: "OK",
    400: "Bad Request",
    500: "Internal Server Error"
}

def write_status_line(writer: asyncio.StreamWriter, status_code: int) -> None:
    """Write response status line to a stream."""
    if status_code not in code_reason_map:
        writer.write(f"HTTP/1.1 {status_code}\r\n".encode())
    else:
        writer.write(f"HTTP/1.1 {status_code} {code_reason_map[status_code]}\r\n".encode())

def write_body(writer: asyncio.StreamWriter, body: bytes) -> None:
    """Write response body to a stream"""
    writer.write(body)

def write_chunked_body(writer: asyncio.StreamWriter, chunk: bytes) -> None:
    """Write a chunk of a body response"""
    writer.write(f"{hex(len(chunk))[2:]}\r\n".encode())
    writer.write(chunk + b"\r\n")

def write_chunked_body_done(writer: asyncio.StreamWriter, trailers: Headers = None) -> None:
    """Write the end of chunked body response."""
    if trailers is None :
        writer.write(b"0\r\n\r\n")
        return
    else:
        writer.write(b"0\r\n")
        trailers.write(writer)
        writer.write(b"\r\n")

def write_headers(writer: asyncio.StreamWriter, headers: Headers) -> None:
    """Write headers of a response"""
    headers.write(writer)

def write_trailers(writer: asyncio.StreamWriter, trailers: Headers) -> None:
    """Write trailers of a response"""
    trailers.write(writer)

def write(writer: asyncio.StreamWriter, status_code: int, headers: Headers, body: bytes) -> None:
    """Write a non chunked response"""
    write_status_line(writer, status_code)
    write_headers(writer, headers)
    write_body(writer, body)

def add_default_headers(content_len: int, headers: Headers) -> None:
    """Adds default response header"""
    headers.add("Content-Length", str(content_len))
    headers.add("Connection", "close")
