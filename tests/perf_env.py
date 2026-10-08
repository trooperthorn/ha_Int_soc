"""A realistic Home Assistant host for the timing tests: 70 config entries, 2,800 entities,
eight users and 25 custom integrations of 15 modules each on disk. Not a test module."""
from __future__ import annotations

import asyncio
import importlib
import json
import os
import sys
import time
from pathlib import Path

from homeassistant import loader
from homeassistant.auth.const import GROUP_ID_ADMIN, GROUP_ID_USER
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

N_CUSTOM = 25
N_BUILT_IN = 39
N_ESPHOME = 6
ENTITIES_PER_ENTRY = 40
USERS = 8

_CORE_DOMAINS = Path(__file__).parent / "fixtures" / "core_domains.txt"


def custom_domain(index: int) -> str:
    return f"cust{index:02d}"


def entry_domains() -> list[str]:
    core = _CORE_DOMAINS.read_text(encoding="utf-8").split()[:N_BUILT_IN]
    # Six ESPHome devices share one domain.
    return [custom_domain(i) for i in range(N_CUSTOM)] + core + ["esphome"] * N_ESPHOME


def write_custom_integrations(config_dir: str) -> None:
    """25 custom integrations, each with a manifest and 15 modules of 120 small functions."""
    root = os.path.join(config_dir, "custom_components")
    for index in range(N_CUSTOM):
        base = os.path.join(root, custom_domain(index))
        os.makedirs(base, exist_ok=True)
        with open(os.path.join(base, "manifest.json"), "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "domain": custom_domain(index),
                    "name": f"Cust {index}",
                    "version": "1.0.0",
                    "requirements": [],
                    "documentation": "https://x.example",
                    "codeowners": [],
                },
                handle,
            )
        for module in range(15):
            body = "\n".join(
                f"def fn_{module}_{k}(a, b):\n    return a + b + {k}\n" for k in range(120)
            )
            with open(os.path.join(base, f"mod{module}.py"), "w", encoding="utf-8") as handle:
                handle.write("import os\nimport json\n" + body)


async def build_env(hass, config_dir: str) -> list[MockConfigEntry]:
    """Create the on-disk integrations, then the entries, devices, entities and users."""
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    os.makedirs(config_dir, exist_ok=True)
    with open(os.path.join(config_dir, "configuration.yaml"), "w", encoding="utf-8") as handle:
        handle.write("homeassistant:\n  name: Home\n")
    write_custom_integrations(config_dir)
    entries = []
    for i, domain in enumerate(entry_domains()):
        entry = MockConfigEntry(domain=domain, title=f"{domain} {i}", data={}, unique_id=f"u{i}")
        entry.add_to_hass(hass)
        entries.append(entry)
        device = dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id, identifiers={(domain, f"dev{i}")}, name=f"Device {i}"
        )
        for j in range(ENTITIES_PER_ENTRY):
            platform = ("sensor", "binary_sensor", "switch", "light")[j % 4]
            ent = ent_reg.async_get_or_create(
                platform, domain, f"{i}_{j}", config_entry=entry, device_id=device.id,
                suggested_object_id=f"{domain}_{i}_{j}",
            )
            state = ("unavailable", "unknown", "21.5")[j % 3] if j % 9 == 0 else "on"
            hass.states.async_set(ent.entity_id, state, {"friendly_name": ent.entity_id})
    for u in range(USERS):
        user = await hass.auth.async_create_user(
            f"user{u}", group_ids=[GROUP_ID_ADMIN if u < 2 else GROUP_ID_USER]
        )
        for t in range(3):
            await hass.auth.async_create_refresh_token(
                user, client_id=f"https://c{t}.example/", client_name=f"client{t}"
            )
    return entries


def expose_custom_integrations(hass, config_dir: str) -> None:
    """Let the loader find the integrations written under the private config directory.

    The copy of the test config directory makes custom_components a regular package, which
    Python leaves out of the namespace package that holds HA SOC. Dropping its __init__.py
    (in the private copy only) makes it one more portion of that namespace.
    """
    marker = os.path.join(config_dir, "custom_components", "__init__.py")
    if os.path.exists(marker):
        os.remove(marker)
    sys.path.append(config_dir)
    importlib.invalidate_caches()
    hass.data.pop(loader.DATA_CUSTOM_COMPONENTS, None)


def forget_custom_integrations(config_dir: str) -> None:
    try:
        sys.path.remove(config_dir)
    except ValueError:
        pass


class LoopLag:
    """How long the event loop was held, measured two ways.

    ``max_stall`` is wall time: a task asks to wake every 5 ms and how late it wakes is how
    long something held the loop, including waiting for the interpreter lock behind an
    executor thread and waiting for a CPU on a busy machine. It is reported, not asserted,
    because another process can make it any size.

    ``max_callback`` is the most CPU time the loop thread spent inside one callback. It is
    the work the code under test puts on the loop in one go, and does not change when other
    tests share the machine, so the bounds are asserted on it.

    The test harness runs the loop in debug mode, where every future and callback records a
    stack trace (about 5 ms each, growing with the number of executor jobs). Production does
    not, so the measurement turns debug mode off and puts it back afterwards.
    """

    INTERVAL = 0.005

    def __init__(self) -> None:
        self.max_stall = 0.0
        self.max_callback = 0.0
        self._task: asyncio.Task | None = None
        self._was_debug = False
        self._original_run = None

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        last = loop.time()
        while True:
            await asyncio.sleep(self.INTERVAL)
            current = loop.time()
            self.max_stall = max(self.max_stall, current - last - self.INTERVAL)
            last = current

    def start(self) -> None:
        loop = asyncio.get_running_loop()
        self._was_debug = loop.get_debug()
        loop.set_debug(False)
        original = self._original_run = asyncio.events.Handle._run
        lag = self

        def timed_run(handle) -> None:
            started = time.thread_time()
            try:
                original(handle)
            finally:
                lag.max_callback = max(lag.max_callback, time.thread_time() - started)

        asyncio.events.Handle._run = timed_run
        self._task = loop.create_task(self._run())

    async def stop(self) -> float:
        assert self._task is not None
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        asyncio.events.Handle._run = self._original_run
        asyncio.get_running_loop().set_debug(self._was_debug)
        return self.max_stall


def now() -> float:
    return time.perf_counter()
