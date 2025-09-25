"""An example HTTP1.1 Server"""
import hashlib
import asyncio
import requests
import server
import request
import response
from headers import Headers

# Port to listen to
PORT = 42069

async def handle(req: request.Request, writer: asyncio.StreamWriter) -> None:
    """My coroutine handler"""
    hs = Headers()

    if req.request_line.request_target == "/yourproblem":
        hs.add("Content-Type", "text/html")
        response.write(writer, 400, hs, b"""<html>
  <head>
    <title>400 Bad Request</title>
  </head>
  <body>
    <h1>Bad Request</h1>
    <p>Your request honestly kinda sucked.</p>
  </body>
</html>""")
    elif req.request_line.request_target == "/myproblem":
        hs.add("Content-Type", "text/html")
        response.write(writer, 500, hs, b"""<html>
  <head>
    <title>500 Internal Server Error</title>
  </head>
  <body>
    <h1>Internal Server Error</h1>
    <p>Okay, you know what? This one is on me.</p>
  </body>
</html>""")

    elif req.request_line.request_target == "/chunked":
        hs.add("Transfer-Encoding", "chunked")
        hs.add("Content-Type", "text/plain")
        response.write_status_line(writer, 200)
        response.write_headers(writer, hs)
        for i in range(0, 100):
            response.write_chunked_body(writer, chr(i) * (i+1))
            await asyncio.sleep(0.1)
        response.write_chunked_body_done(writer)

    elif req.request_line.request_target.startswith("/httpbin/"):
      resp = requests.get("https://httpbin.org/" + req.request_line.request_target.split("/httpbin/")[1], stream=True, timeout=10)

      if resp.status_code != 200:
        hs.add("Content-Type", "text/plain")
        response.write(writer, resp.status_code, hs, b"HTTP BIN ERROR")
      else:
        hasher = hashlib.sha256()
        content_len = 0
        hs.add("Transfer-Encoding", "chunked")
        hs.add("Content-Type", "text/plain")
        response.write_status_line(writer, 200)
        response.write_headers(writer, hs)
        for chunk in resp.iter_content(chunk_size=1024):
          response.write_chunked_body(writer, chunk)
          hasher.update(chunk)
          content_len += len(chunk)
        trailers = Headers()
        trailers.add("X-Content-SHA256", hasher.hexdigest())
        trailers.add("X-Content-Length", str(content_len))
        response.write_chunked_body_done(writer, trailers=trailers)

    elif req.request_line.request_target == "/video":
        hs.add("Content-Type", "video.mp4")
        video = open("assets/vim.mp4", "rb")
        response.write(writer, 200, hs, video.read())
    else:
        hs.add("Content-Type", "text/html")
        response.write(writer, 200, hs, b"""<html>
  <head>
    <title>200 OK</title>
  </head>
  <body>
    <h1>Success!</h1>
    <p>Your request was an absolute banger.</p>
  </body>
</html>""")

async def main():
    """Main function"""
    async with server.Server(PORT, handle) as srv:
        await srv.serve()

if __name__ == "__main__":
    asyncio.run(main())
