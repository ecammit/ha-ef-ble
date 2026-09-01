import pytest
from pytest_mock import MockerFixture

from custom_components.ef_ble.eflib.connection import Connection
from custom_components.ef_ble.eflib.exceptions import UnsupportedBluetoothProtocol


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
    mocker.patch(
        "custom_components.ef_ble.eflib.connection.close_stale_connections_by_address",
        mocker.AsyncMock(),
    )
    mock_client = mocker.Mock()
    mock_client.is_connected = False
    mock_client.clear_cache = mocker.AsyncMock()
    mocker.patch(
        "custom_components.ef_ble.eflib.connection.establish_connection",
        mocker.AsyncMock(return_value=mock_client),
    )
    yield conn, mock_client
    conn._cancel_tasks()


async def test_clears_gatt_cache_on_a_partially_populated_service_table(
    connection, mocker: MockerFixture
):
    """
    BlueZ can hand back a stale service table that isn't empty - just missing the
    characteristic we need (e.g. only the generic Service Changed characteristic) -
    which must still trigger a cache clear, the same as a fully empty table does.
    """
    conn, mock_client = connection
    mocker.patch.object(
        conn,
        "_validate_characteristics",
        side_effect=UnsupportedBluetoothProtocol(
            "notify", ["00002a05-0000-1000-8000-00805f9b34fb Service Changed"]
        ),
    )

    await conn.connect(max_attempts=1)

    mock_client.clear_cache.assert_awaited_once()


async def test_clears_gatt_cache_on_an_empty_service_table(
    connection, mocker: MockerFixture
):
    conn, mock_client = connection
    mocker.patch.object(
        conn,
        "_validate_characteristics",
        side_effect=UnsupportedBluetoothProtocol("notify", []),
    )

    await conn.connect(max_attempts=1)

    mock_client.clear_cache.assert_awaited_once()
