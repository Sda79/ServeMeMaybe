import asyncio
from typing import Dict, Tuple

WS = 32

def is_field_name_valid(field_name: bytes) -> bool:
    if len(field_name) < 1:
        return False
    if field_name[-1] == WS:
        return False
    for char in field_name:

        if char >= int.from_bytes(b'0') and char <= int.from_bytes(b'9'):
            continue
        elif char >= int.from_bytes(b'a') and char <= int.from_bytes(b'z'):
            continue
        elif char >= int.from_bytes(b'A') and char <= int.from_bytes(b'Z'):
            continue
        elif char in b"!#$%&'*+-.^_`|~'":
            continue
        else:
            return False
    return True

class Headers():
    def __init__(self):
        self._headers: Dict[str, str] = {}

    def __str__(self):
        result: str = "Headers:\n"
        for key, value in self._headers.items():
            result += f"- {key}: {value}\n"
        return result
    
    def get(self, field: str) -> str:
        return self._headers[field.lower()]
    
    def add(self, field: str, value: str) -> None:
        field = field.lower()
        if field not in self._headers:
            self._headers[field] = value
        else:
            self._headers += ", " + value

    def write(self, writer: asyncio.StreamWriter) -> None:
        for field, value in self._headers.items():
            writer.write(f"{field}: {value}\r\n".encode())
        writer.write(b"\r\n")

    def parse(self, data: bytes) -> Tuple[int, bool]:
        if b"\r\n" not in data:
            return 0, False
        if data.startswith(b"\r\n"):
            return len(b"\r\n"), True

        header_line: bytes = data.split(b"\r\n", 1)[0]
        header_name, header_value = header_line.split(b":", 1)
        header_name = header_name.lstrip()
        header_value = header_value.strip()

        if not is_field_name_valid(header_name):
            raise ValueError(f"Malformed header name {header_name}")
        
        header_name = header_name.lower()
        if header_name.decode() in self._headers:
            self._headers[header_name.decode()] += ", " + header_value.decode()
        else:
            self._headers[header_name.decode()] = header_value.decode()

        return len(header_line) + len(b"\r\n"), False
