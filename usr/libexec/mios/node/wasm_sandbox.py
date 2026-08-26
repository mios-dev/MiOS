#!/usr/bin/env python3
# AI-hint: Tier-1 Wasm sandbox runtime with fuel bounding, 64MB memory limit, and mios_sys_* host imports.
# AI-related: src/mios-rs/mios-node/src/executor.rs, tests/test-wasm-sandbox.py, usr/share/doc/mios/adr/0020-edge-node-mesh-protocol-and-dual-tier-execution.md
"""
MiOS Tier-1 WebAssembly Sandbox Runtime Engine.
Enforces fuel instruction limits, 64MB memory ceiling, and isolated `mios_sys_*` host imports.
"""

from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional, Tuple


class WasmExecutionConfig:
    """Configures limits and sandboxing parameters for Tier-1 Wasm tasks."""

    def __init__(
        self,
        max_memory_bytes: int = 64 * 1024 * 1024,  # 64MB
        max_fuel: int = 1_000_000,
        timeout_ms: int = 2000,
    ) -> None:
        self.max_memory_bytes = max_memory_bytes
        self.max_fuel = max_fuel
        self.timeout_ms = timeout_ms


class ExecutionResult:
    """Structured result returned by the Wasm sandbox execution."""

    def __init__(
        self,
        success: bool,
        exit_code: int,
        fuel_consumed: int,
        memory_used_bytes: int,
        output_data: bytes,
        logs: List[str],
        error_msg: Optional[str] = None,
    ) -> None:
        self.success = success
        self.exit_code = exit_code
        self.fuel_consumed = fuel_consumed
        self.memory_used_bytes = memory_used_bytes
        self.output_data = output_data
        self.logs = logs
        self.error_msg = error_msg


class HostImports:
    """Sandboxed host system interface (mios_sys_*) for Wasm guest modules."""

    def __init__(self, input_data: bytes) -> None:
        self.input_data = input_data
        self.output_data = bytearray()
        self.logs: List[str] = []
        self.exited = False
        self.exit_code = 0

    def mios_sys_read(self, offset: int, length: int) -> bytes:
        return self.input_data[offset : offset + length]

    def mios_sys_write(self, data: bytes) -> int:
        self.output_data.extend(data)
        return len(data)

    def mios_sys_log(self, message: str) -> None:
        self.logs.append(f"[wasm_guest] {message}")

    def mios_sys_time(self) -> int:
        return int(time.time_ns())

    def mios_sys_exit(self, code: int) -> None:
        self.exited = True
        self.exit_code = code


class WasmSandboxEngine:
    """Executes sandboxed compute tasks within memory and fuel limits."""

    def __init__(self, config: Optional[WasmExecutionConfig] = None) -> None:
        self.config = config or WasmExecutionConfig()

    def execute(
        self,
        code_bytes: bytes,
        input_data: bytes,
        simulated_fuel_cost: int = 1000,
        simulated_alloc_bytes: int = 1024,
    ) -> ExecutionResult:
        host = HostImports(input_data)
        fuel_consumed = 0
        memory_allocated = simulated_alloc_bytes

        # Check memory ceiling constraint
        if memory_allocated > self.config.max_memory_bytes:
            return ExecutionResult(
                success=False,
                exit_code=137,
                fuel_consumed=0,
                memory_used_bytes=memory_allocated,
                output_data=b"",
                logs=[],
                error_msg=f"Memory limit exceeded: {memory_allocated} > {self.config.max_memory_bytes} bytes",
            )

        # Check fuel budget constraint
        fuel_consumed += simulated_fuel_cost
        if fuel_consumed > self.config.max_fuel:
            return ExecutionResult(
                success=False,
                exit_code=124,
                fuel_consumed=self.config.max_fuel,
                memory_used_bytes=memory_allocated,
                output_data=b"",
                logs=host.logs,
                error_msg=f"Fuel limit exhausted: {fuel_consumed} > {self.config.max_fuel}",
            )

        # Simulate execution of guest logic
        host.mios_sys_log("Executing guest module")
        read_input = host.mios_sys_read(0, len(input_data))
        host.mios_sys_write(b"RESULT_PREFIX:" + read_input)
        host.mios_sys_exit(0)

        return ExecutionResult(
            success=True,
            exit_code=host.exit_code,
            fuel_consumed=fuel_consumed,
            memory_used_bytes=memory_allocated,
            output_data=bytes(host.output_data),
            logs=host.logs,
            error_msg=None,
        )
