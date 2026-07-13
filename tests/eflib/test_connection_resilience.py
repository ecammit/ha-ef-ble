import time

import pytest
from bleak_retry_connector import BleakOutOfConnectionSlotsError
from pytest_mock import MockerFixture

from custom_components.ef_ble.eflib.connection import (
    MAX_RECONNECT_ATTEMPTS,
    RECONNECT_BASE_DELAY,
    RECONNECT_MAX_DELAY,
    WATCHDOG_TIMEOUT,
    Connection,
    ConnectionState,
    MaxConnectionAttemptsReached,
    _next_reconnect_delay,
)


@pytest.mark.parametrize(
    ("attempt", "expected_base"),
    [(1, 10.0), (2, 20.0), (3, 40.0), (4, 60.0), (5, 60.0)],
)
def test_next_reconnect_delay_grows_and_caps(
    mocker: MockerFixture, attempt, expected_base
):
    mocker.patch("random.uniform", return_value=0.0)
    assert _next_reconnect_delay(attempt) == expected_base


def test_next_reconnect_delay_jitter_stays_within_bounds():
    for attempt in range(1, 6):
        base = min(RECONNECT_BASE_DELAY * (2 ** (attempt - 1)), RECONNECT_MAX_DELAY)
        delay = _next_reconnect_delay(attempt)
        assert base <= delay <= base * 1.2


@pytest.fixture
async def connection(mocker: MockerFixture):
    ble_dev = mocker.Mock()
    ble_dev.address = "AA:BB:CC:DD:EE:FF"
    conn = Connection(
        ble_dev=ble_dev,
        dev_sn="TEST1234",
        user_id="user",
        data_parse=mocker.AsyncMock(),
        packet_parse=mocker.AsyncMock(),
    )
    yield conn
    conn._cancel_tasks()


def test_construction_does_not_schedule_watchdog_task(connection):
    assert len(connection._tasks) == 0


async def test_connect_schedules_watchdog_task_once(connection, mocker: MockerFixture):
    mocker.patch(
        "custom_components.ef_ble.eflib.connection.establish_connection",
        side_effect=BleakOutOfConnectionSlotsError("no free slots"),
    )
    connection.with_disabled_reconnect()

    await connection.connect(max_attempts=1)
    with pytest.raises(MaxConnectionAttemptsReached):
        await connection.connect(max_attempts=1)

    assert len(connection._tasks) == 1


def test_ble_dev_without_resolver_returns_cached_device(connection):
    assert connection.ble_dev() is connection._ble_dev


def test_ble_dev_uses_resolved_device_when_available(connection, mocker: MockerFixture):
    resolved = mocker.Mock()
    connection.with_ble_device_resolver(lambda: resolved)

    assert connection.ble_dev() is resolved


def test_ble_dev_falls_back_to_cached_device_when_resolver_returns_none(
    connection,
):
    cached = connection._ble_dev
    connection.with_ble_device_resolver(lambda: None)

    assert connection.ble_dev() is cached


async def test_connect_records_out_of_slots_error(connection, mocker: MockerFixture):
    mocker.patch(
        "custom_components.ef_ble.eflib.connection.establish_connection",
        side_effect=BleakOutOfConnectionSlotsError("no free slots"),
    )
    connection.with_disabled_reconnect()

    await connection.connect(max_attempts=1)

    assert connection._last_state == ConnectionState.ERROR_OUT_OF_SLOTS


async def test_connect_resets_last_activity_once_connected(
    connection, mocker: MockerFixture
):
    mock_client = mocker.AsyncMock()
    mock_client.is_connected = True
    mocker.patch(
        "custom_components.ef_ble.eflib.connection.establish_connection",
        return_value=mock_client,
    )
    mocker.patch.object(connection, "initBleSessionKey", mocker.AsyncMock())
    connection._last_activity = 0.0

    await connection.connect(max_attempts=1)

    assert time.monotonic() - connection._last_activity < 1.0


async def test_watchdog_forces_disconnect_after_timeout(
    connection, mocker: MockerFixture
):
    disconnect_client = mocker.patch.object(connection, "_disconnect_client")
    connection._last_activity = time.monotonic() - (WATCHDOG_TIMEOUT + 1)

    await connection._watchdog_check()

    disconnect_client.assert_awaited_once()


async def test_watchdog_does_not_disconnect_when_recently_active(
    connection, mocker: MockerFixture
):
    disconnect_client = mocker.patch.object(connection, "_disconnect_client")
    connection._last_activity = time.monotonic()

    await connection._watchdog_check()

    disconnect_client.assert_not_awaited()


def test_options_default_watchdog_enabled_and_max_reconnect_attempts():
    options = Connection.Options()

    assert options.watchdog_enabled is True
    assert options.watchdog_timeout == WATCHDOG_TIMEOUT
    assert options.max_reconnect_attempts == MAX_RECONNECT_ATTEMPTS


async def test_watchdog_disabled_via_options_does_not_disconnect(
    connection, mocker: MockerFixture
):
    disconnect_client = mocker.patch.object(connection, "_disconnect_client")
    connection._options.watchdog_enabled = False
    connection._last_activity = time.monotonic() - (WATCHDOG_TIMEOUT + 1)

    await connection._watchdog_check()

    disconnect_client.assert_not_awaited()


async def test_watchdog_honors_custom_timeout_option(connection, mocker: MockerFixture):
    disconnect_client = mocker.patch.object(connection, "_disconnect_client")
    connection._options.watchdog_timeout = 5.0
    connection._last_activity = time.monotonic() - 10

    await connection._watchdog_check()

    disconnect_client.assert_awaited_once()


async def test_watchdog_does_not_disconnect_within_custom_timeout(
    connection, mocker: MockerFixture
):
    disconnect_client = mocker.patch.object(connection, "_disconnect_client")
    connection._options.watchdog_timeout = 120.0
    connection._last_activity = time.monotonic() - (WATCHDOG_TIMEOUT + 1)

    await connection._watchdog_check()

    disconnect_client.assert_not_awaited()


async def test_reconnect_honors_max_reconnect_attempts_option(connection):
    connection._options.max_reconnect_attempts = 1
    connection._reconnect_attempt = 1

    await connection.reconnect()

    assert (
        connection._connection_state
        == ConnectionState.ERROR_MAX_RECONNECT_ATTEMPTS_REACHED
    )
