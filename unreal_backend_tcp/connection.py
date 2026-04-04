"""Connection management for the internal Unreal TCP backend."""

import json
import logging
import socket
import struct
import threading
import time
from typing import Any, Dict, Optional

from unreal_harness_runtime.config import get_unreal_host, get_unreal_port

logger = logging.getLogger("UnrealBackendTCP")


class UnrealConnection:
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 0.5
    MAX_RETRY_DELAY = 5.0
    CONNECT_TIMEOUT = 10
    DEFAULT_RECV_TIMEOUT = 30
    LARGE_OP_RECV_TIMEOUT = 300
    BUFFER_SIZE = 8192

    LARGE_OPERATION_COMMANDS = {
        "get_material_graph",
        "get_assets",
        "get_asset_properties",
        "read_blueprint_content",
        "analyze_blueprint_graph",
        "get_niagara_graph",
        "get_niagara_emitter",
    }

    def __init__(self) -> None:
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self._lock = threading.RLock()
        self._last_error: Optional[str] = None

    def _create_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.CONNECT_TIMEOUT)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 131072)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072)
        try:
            sock.setsockopt(
                socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("hh", 1, 0)
            )
        except OSError:
            pass
        return sock

    def _close_socket_unsafe(self) -> None:
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
        self.connected = False

    def connect(self) -> bool:
        for attempt in range(self.MAX_RETRIES + 1):
            with self._lock:
                self._close_socket_unsafe()
                try:
                    host = get_unreal_host()
                    port = get_unreal_port()
                    logger.info(
                        "Connecting to Unreal at %s:%s (attempt %s)...",
                        host,
                        port,
                        attempt + 1,
                    )
                    self.socket = self._create_socket()
                    self.socket.connect((host, port))
                    self.connected = True
                    self._last_error = None
                    return True
                except socket.timeout as exc:
                    self._last_error = f"Connection timeout: {exc}"
                except ConnectionRefusedError as exc:
                    self._last_error = f"Connection refused: {exc}"
                except OSError as exc:
                    self._last_error = f"OS error: {exc}"
                except Exception as exc:
                    self._last_error = f"Unexpected error: {exc}"
                self._close_socket_unsafe()
                self.connected = False

            if attempt < self.MAX_RETRIES:
                delay = min(self.BASE_RETRY_DELAY * (2**attempt), self.MAX_RETRY_DELAY)
                time.sleep(delay)

        logger.error("Failed to connect after %s attempts", self.MAX_RETRIES + 1)
        return False

    def disconnect(self) -> None:
        with self._lock:
            self._close_socket_unsafe()

    def _get_timeout_for_command(self, command_type: str) -> int:
        if command_type in self.LARGE_OPERATION_COMMANDS:
            return self.LARGE_OP_RECV_TIMEOUT
        return self.DEFAULT_RECV_TIMEOUT

    def _receive_response(self, command_type: str) -> bytes:
        if not self.socket:
            raise ConnectionError("Socket not connected")

        timeout = self._get_timeout_for_command(command_type)
        self.socket.settimeout(timeout)
        chunks = []
        start_time = time.time()

        try:
            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    raise socket.timeout(f"Overall timeout after {elapsed:.1f}s")

                try:
                    chunk = self.socket.recv(self.BUFFER_SIZE)
                except socket.timeout:
                    if chunks:
                        data = b"".join(chunks)
                        try:
                            json.loads(data.decode("utf-8"))
                            return data
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            pass
                    raise

                if not chunk:
                    if not chunks:
                        raise ConnectionError(
                            "Connection closed before receiving any data"
                        )
                    break

                chunks.append(chunk)
                data = b"".join(chunks)
                try:
                    json.loads(data.decode("utf-8"))
                    return data
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
        except socket.timeout as exc:
            if chunks:
                data = b"".join(chunks)
                try:
                    json.loads(data.decode("utf-8"))
                    return data
                except Exception:
                    pass
            raise TimeoutError("Timeout waiting for response") from exc

        raise ConnectionError("Connection closed without response")

    def _send_command_once(
        self, command: str, params: Optional[Dict[str, Any]], attempt: int
    ) -> Dict[str, Any]:
        with self._lock:
            if not self.connect():
                raise ConnectionError(
                    f"Failed to connect to Unreal Engine: {self._last_error}"
                )

            try:
                if not self.socket:
                    raise ConnectionError("Socket not connected")

                command_json = json.dumps({"type": command, "params": params or {}})
                self.socket.settimeout(10)
                self.socket.sendall(command_json.encode("utf-8"))
                response_data = self._receive_response(command)
                response = json.loads(response_data.decode("utf-8"))

                if response.get("status") == "error":
                    logger.warning("Unreal returned error: %s", response.get("error"))
                elif response.get("success") is False:
                    response = {
                        "status": "error",
                        "error": response.get("error")
                        or response.get("message", "Unknown error"),
                    }

                return response
            finally:
                self._close_socket_unsafe()

    def send_command(
        self, command: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        last_error: Optional[str] = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return self._send_command_once(command, params, attempt)
            except (ConnectionError, TimeoutError, socket.error, OSError) as exc:
                last_error = str(exc)
                logger.warning("Command failed (attempt %s): %s", attempt + 1, exc)
                self.disconnect()
                if attempt < self.MAX_RETRIES:
                    delay = min(
                        self.BASE_RETRY_DELAY * (2**attempt), self.MAX_RETRY_DELAY
                    )
                    time.sleep(delay)
            except Exception as exc:
                logger.error("Unexpected error sending command: %s", exc)
                self.disconnect()
                return {"status": "error", "error": str(exc)}

        return {
            "status": "error",
            "error": f"Command failed after {self.MAX_RETRIES + 1} attempts: {last_error}",
        }


_unreal_connection: Optional[UnrealConnection] = None
_connection_lock = threading.Lock()


def get_unreal_connection() -> UnrealConnection:
    global _unreal_connection
    with _connection_lock:
        if _unreal_connection is None:
            _unreal_connection = UnrealConnection()
        return _unreal_connection


def reset_unreal_connection() -> None:
    global _unreal_connection
    with _connection_lock:
        if _unreal_connection:
            _unreal_connection.disconnect()
            _unreal_connection = None
