import asyncio

import pytest
from pytest_mock import MockerFixture

from custom_components.ef_ble.eflib.connection import Connection, ConnectionState


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
    conn._client = mocker.Mock()
    conn._client.is_connected = True
    yield conn
    conn._cancel_tasks()


async def test_notification_queued_when_buffer_is_open(
    connection, mocker: MockerFixture
):
    """
    A notification arriving while an auth stage is expecting a response is queued
    for that stage rather than treated as ordinary device data.
    """
    listen_for_data_handler = mocker.patch.object(
        connection, "_listen_for_data_handler"
    )
    connection._notification_queue = asyncio.Queue()

    await connection._on_notification(mocker.Mock(), bytearray(b"\x01\x02\x03"))

    listen_for_data_handler.assert_not_called()
    assert connection._notification_queue.get_nowait() == b"\x01\x02\x03"


async def test_notification_falls_through_when_buffer_is_closed(
    connection, mocker: MockerFixture
):
    """Outside an auth stage's response wait, a notification is ordinary device data."""
    listen_for_data_handler = mocker.patch.object(
        connection, "_listen_for_data_handler"
    )
    connection._notification_queue = None

    await connection._on_notification(mocker.Mock(), bytearray(b"\x01\x02\x03"))

    listen_for_data_handler.assert_awaited_once_with(b"\x01\x02\x03")


async def test_expecting_response_drains_unread_notifications_on_exit(
    connection, mocker: MockerFixture
):
    """
    Anything left in the buffer when a stage is done with it is still device data, and
    the frame assembler needs every byte in order - so it must be replayed through
    `_listen_for_data_handler`, not silently discarded.
    """
    listen_for_data_handler = mocker.patch.object(
        connection, "_listen_for_data_handler"
    )

    async with connection._expecting_response():
        connection._notification_queue.put_nowait(b"\x01")
        connection._notification_queue.put_nowait(b"\x02")

    assert connection._notification_queue is None
    assert listen_for_data_handler.await_args_list == [
        mocker.call(b"\x01"),
        mocker.call(b"\x02"),
    ]


async def test_listen_for_data_handler_drops_data_before_session_key_exists(
    connection, mocker: MockerFixture
):
    """
    A notification that reaches the fallback path before a session key exists can't
    be legitimate device data - there's nothing to decrypt it with, or (worse, after a
    reconnect) a stale key left over from the previous session is still sitting there.
    Either way it must be dropped, not handed to `_parse_enc_packets`, which is what
    turned a stray notification into an `AssertionError` or a silent bad decode
    ("prefix is incorrect") in the reported bugs.
    """
    connection._connection_state = ConnectionState.CONNECTED
    parse_enc_packets = mocker.patch.object(connection, "_parse_enc_packets")

    await connection._listen_for_data_handler(b"\x01\x02\x03")

    parse_enc_packets.assert_not_called()


async def test_listen_for_data_handler_parses_data_once_session_key_exists(
    connection, mocker: MockerFixture
):
    connection._connection_state = ConnectionState.AUTHENTICATING
    parse_enc_packets = mocker.patch.object(
        connection, "_parse_enc_packets", mocker.AsyncMock(return_value=[])
    )

    await connection._listen_for_data_handler(b"\x01\x02\x03")

    parse_enc_packets.assert_awaited_once_with(b"\x01\x02\x03")


async def test_connect_survives_a_stray_notification_during_subscribe(
    connection, mocker: MockerFixture
):
    """
    End-to-end regression test: a notification delivered the instant the
    characteristic is (re-)subscribed - before any auth stage is even waiting for a
    response - must not crash or corrupt the handshake. It has no session key to be
    decrypted with yet, so it's dropped, and the real auth flow proceeds normally.
    """
    connection._connection_state = ConnectionState.NOT_CONNECTED
    connection._client = None  # the fixture's pre-connected mock would short-circuit
    mock_client = mocker.Mock()
    mock_client.is_connected = True
    mocker.patch(
        "custom_components.ef_ble.eflib.connection.establish_connection",
        mocker.AsyncMock(return_value=mock_client),
    )
    mocker.patch.object(connection, "_validate_characteristics")

    async def fake_start_notify(callback):
        await callback(mocker.Mock(), bytearray(b"\x99\x99\x99"))

    mocker.patch.object(connection, "_start_notify", side_effect=fake_start_notify)
    run_auth = mocker.patch.object(connection, "_run_auth", mocker.AsyncMock())

    await connection.connect(max_attempts=1)

    # `_run_auth()` is only scheduled as a task here, not awaited inline - the point of
    # this test is that connect() itself gets there at all, rather than raising or
    # disconnecting because of the stray notification.
    run_auth.assert_called_once()
    assert not connection._state.is_error
