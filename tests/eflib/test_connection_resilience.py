import pytest
from bleak_retry_connector import BleakOutOfConnectionSlotsError
from pytest_mock import MockerFixture

from custom_components.ef_ble.eflib.connection import (
    RECONNECT_BASE_DELAY,
    RECONNECT_MAX_DELAY,
    Connection,
    ConnectionState,
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
def connection(mocker: MockerFixture):
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
