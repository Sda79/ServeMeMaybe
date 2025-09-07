#!/usr/bin/env python3 -u
import asyncio
import sys
from typing import List

async def consumer(queue: asyncio.Queue[str], peer: str) -> None:
    """Coroutine that consume string lines from a Queue and print them to stdout"""
    print(f"Starting consumer for {peer}")
    while True:
        try:
            line = await queue.get()
            print(f"from: {peer} read: {line}")
            queue.task_done()
        except asyncio.QueueShutDown:
            break
    print(f"Consumer for {peer} shutted down")
    sys.stdout.flush()

async def get_lines_to_queue(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Coroutine that reads lines from a TCP reader until EOF and sends them to a consumer via a queue"""
    print("TCP Connection accepted")
    queue: asyncio.Queue[str] = asyncio.Queue()
    peer: str = writer.get_extra_info("peername")

    # start a consumer for this TCP connection
    asyncio.create_task(consumer(queue, peer))

    # init current line empty
    current_line: bytes = b""
    # read first 8 byte chunk
    chunk: bytes = await reader.read(8)
    # until EOF
    while chunk != b"": 
        # split the chunk by carriage return
        parts: List[bytes] = chunk.split(b'\n')
        if len(parts) == 1: # the chunk doesn't contain the end of a line
            current_line += parts[0] # append chunk to the current line
        else:
            for i in range(0, len(parts) - 1): # for each part excepte the last one
                current_line += parts[i]
                queue.put_nowait(current_line.decode("utf-8"))
                current_line = b"" # reset the current line
            current_line = parts[-1] # add the last part to the current line
        chunk = await reader.read(8) # read the next chunk
    if current_line != b"": # flush the current line
        queue.put_nowait(current_line.decode("utf-8"))

    writer.close()
    await writer.wait_closed()
    print("TCP Connection closed")
    queue.shutdown()


async def main():
    server = await asyncio.start_server(get_lines_to_queue, "127.0.0.1", 42069)
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')
    async with server:
        await server.serve_forever()


asyncio.run(main())