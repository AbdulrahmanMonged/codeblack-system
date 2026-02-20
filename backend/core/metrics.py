from __future__ import annotations

from collections import Counter
from threading import Lock


class MetricsRegistry:
    HTTP_DURATION_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    IPC_DURATION_BUCKETS = (0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0)

    def __init__(self) -> None:
        self._lock = Lock()
        self._http_requests_total: Counter[tuple[str, str, str]] = Counter()
        self._http_request_duration_seconds_sum: Counter[tuple[str, str]] = Counter()
        self._http_request_duration_seconds_count: Counter[tuple[str, str]] = Counter()
        self._http_request_duration_seconds_bucket: Counter[tuple[str, str, str]] = (
            Counter()
        )
        self._ipc_commands_total: Counter[tuple[str, str]] = Counter()
        self._ipc_retries_total: Counter[tuple[str]] = Counter()
        self._ipc_command_duration_seconds_sum: Counter[tuple[str]] = Counter()
        self._ipc_command_duration_seconds_count: Counter[tuple[str]] = Counter()
        self._ipc_command_duration_seconds_bucket: Counter[tuple[str, str]] = Counter()
        self._rate_limit_rejections_total: Counter[tuple[str]] = Counter()
        self._authz_failures_total: Counter[tuple[str, str]] = Counter()

    def record_http_request(
        self,
        *,
        method: str,
        route_path: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        status = str(status_code)
        labels = (method.upper(), route_path, status)
        histogram_key = (method.upper(), route_path)
        with self._lock:
            self._http_requests_total[labels] += 1
            self._http_request_duration_seconds_sum[histogram_key] += max(
                0.0, duration_seconds
            )
            self._http_request_duration_seconds_count[histogram_key] += 1
            for bucket in self.HTTP_DURATION_BUCKETS:
                if duration_seconds <= bucket:
                    self._http_request_duration_seconds_bucket[
                        (histogram_key[0], histogram_key[1], str(bucket))
                    ] += 1
            self._http_request_duration_seconds_bucket[
                (histogram_key[0], histogram_key[1], "+Inf")
            ] += 1

    def record_ipc_command(self, *, command_type: str, result: str) -> None:
        with self._lock:
            self._ipc_commands_total[(command_type, result)] += 1

    def record_ipc_retry(self, *, command_type: str) -> None:
        with self._lock:
            self._ipc_retries_total[(command_type,)] += 1

    def record_ipc_duration(self, *, command_type: str, duration_seconds: float) -> None:
        key = (command_type,)
        with self._lock:
            self._ipc_command_duration_seconds_sum[key] += max(0.0, duration_seconds)
            self._ipc_command_duration_seconds_count[key] += 1
            for bucket in self.IPC_DURATION_BUCKETS:
                if duration_seconds <= bucket:
                    self._ipc_command_duration_seconds_bucket[
                        (command_type, str(bucket))
                    ] += 1
            self._ipc_command_duration_seconds_bucket[(command_type, "+Inf")] += 1

    def record_rate_limit_rejection(self, *, scope: str) -> None:
        with self._lock:
            self._rate_limit_rejections_total[(scope,)] += 1

    def record_authz_failure(self, *, scope: str, status_code: int) -> None:
        with self._lock:
            self._authz_failures_total[(scope, str(status_code))] += 1

    def render_prometheus(self) -> str:
        with self._lock:
            lines: list[str] = []

            lines.extend(
                [
                    "# HELP codeblack_http_requests_total Total HTTP requests by route.",
                    "# TYPE codeblack_http_requests_total counter",
                ]
            )
            for (method, path, status), value in sorted(self._http_requests_total.items()):
                lines.append(
                    f'codeblack_http_requests_total{{method="{_escape(method)}",path="{_escape(path)}",status="{_escape(status)}"}} {value}'
                )

            lines.extend(
                [
                    "# HELP codeblack_http_request_duration_seconds HTTP request latency histogram.",
                    "# TYPE codeblack_http_request_duration_seconds histogram",
                ]
            )
            for (method, path, le), value in sorted(
                self._http_request_duration_seconds_bucket.items()
            ):
                lines.append(
                    f'codeblack_http_request_duration_seconds_bucket{{method="{_escape(method)}",path="{_escape(path)}",le="{_escape(le)}"}} {value}'
                )
            for (method, path), value in sorted(
                self._http_request_duration_seconds_count.items()
            ):
                lines.append(
                    f'codeblack_http_request_duration_seconds_count{{method="{_escape(method)}",path="{_escape(path)}"}} {value}'
                )
            for (method, path), value in sorted(
                self._http_request_duration_seconds_sum.items()
            ):
                lines.append(
                    f'codeblack_http_request_duration_seconds_sum{{method="{_escape(method)}",path="{_escape(path)}"}} {value}'
                )

            lines.extend(
                [
                    "# HELP codeblack_ipc_commands_total Bot IPC command outcomes.",
                    "# TYPE codeblack_ipc_commands_total counter",
                ]
            )
            for (command_type, result), value in sorted(self._ipc_commands_total.items()):
                lines.append(
                    f'codeblack_ipc_commands_total{{command_type="{_escape(command_type)}",result="{_escape(result)}"}} {value}'
                )

            lines.extend(
                [
                    "# HELP codeblack_ipc_retries_total Bot IPC command retry attempts.",
                    "# TYPE codeblack_ipc_retries_total counter",
                ]
            )
            for (command_type,), value in sorted(self._ipc_retries_total.items()):
                lines.append(
                    f'codeblack_ipc_retries_total{{command_type="{_escape(command_type)}"}} {value}'
                )

            lines.extend(
                [
                    "# HELP codeblack_ipc_command_duration_seconds Bot IPC command latency histogram.",
                    "# TYPE codeblack_ipc_command_duration_seconds histogram",
                ]
            )
            for (command_type, le), value in sorted(
                self._ipc_command_duration_seconds_bucket.items()
            ):
                lines.append(
                    f'codeblack_ipc_command_duration_seconds_bucket{{command_type="{_escape(command_type)}",le="{_escape(le)}"}} {value}'
                )
            for (command_type,), value in sorted(
                self._ipc_command_duration_seconds_count.items()
            ):
                lines.append(
                    f'codeblack_ipc_command_duration_seconds_count{{command_type="{_escape(command_type)}"}} {value}'
                )
            for (command_type,), value in sorted(
                self._ipc_command_duration_seconds_sum.items()
            ):
                lines.append(
                    f'codeblack_ipc_command_duration_seconds_sum{{command_type="{_escape(command_type)}"}} {value}'
                )

            lines.extend(
                [
                    "# HELP codeblack_rate_limit_rejections_total Rate-limited HTTP requests.",
                    "# TYPE codeblack_rate_limit_rejections_total counter",
                ]
            )
            for (scope,), value in sorted(self._rate_limit_rejections_total.items()):
                lines.append(
                    f'codeblack_rate_limit_rejections_total{{scope="{_escape(scope)}"}} {value}'
                )

            lines.extend(
                [
                    "# HELP codeblack_authz_failures_total Authorization/authentication failures on privileged paths.",
                    "# TYPE codeblack_authz_failures_total counter",
                ]
            )
            for (scope, status), value in sorted(self._authz_failures_total.items()):
                lines.append(
                    f'codeblack_authz_failures_total{{scope="{_escape(scope)}",status="{_escape(status)}"}} {value}'
                )

            return "\n".join(lines) + "\n"


def _escape(raw: str) -> str:
    return raw.replace("\\", "\\\\").replace('"', '\\"')


metrics_registry = MetricsRegistry()
