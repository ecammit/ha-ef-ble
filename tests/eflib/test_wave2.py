import pytest
from pytest_mock import MockerFixture

from custom_components.ef_ble.eflib import controls, units
from custom_components.ef_ble.eflib.devices.wave2 import (
    Device,
    DrainMode,
    FanGear,
    MainMode,
    PowerMode,
    SubMode,
    WaterLevel,
)

PACKETS = {
    "fan_celsius_target_30": "aa026c00bc2de6b30200012d42214250e4e5f8e45a3990a7e6ece6e7e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e4e7e7e7e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e66d8b9fa7e6e6e4e6e6e6e7e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e6e671a6",
    "heat_celsius_target_30": "aa026c00bc2df8b30200012d42214250f9fbe6fa176d8fb9f8f2f8f9f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8faf9f9f9f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f40681b9f8f8faf8f8f8f9f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8f8b664",
    "heat_celsius_target_16": "aa026c00bc2d2db40200012d422142502c2e3d2f2200ad6c2d272d2c2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2f2c2c2c682d2d2d2d2d2d2d2d2d2d2d2d2d2d2d6b9f576c2d2d2f2d2d2d2c2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d1cd3",
    "fan_fahrenheit_target_86": "aa026c00bc2d7bb40200012d4221425079782d794ab40c397a717b7a7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b797a7a7a7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b63470f397b7b797b7b7b7a7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7b7bc4ac",
    "heat_fahrenheit_target_86": "aa026c00bc2d91b40200012d422142509092c79361a6e8d3909b91909191919191919191919191919191919191919191919191919191919191919191919191919191919191919191919390909091919191919191919191919191919191fb14e2d391919391919190919191919191919191919191919191919191919158e2",
    "heat_drain_off_external": "aa026c00bc2dadb40200012d42214250acae91af6df8d7efaca7adacadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadadafacacacacadadadadadadadadadadadadadadad5ff9d9efadadafadadadacadadadadadadadadadadadadadadadadadadadad8c09",
    "fan_fahrenheit_target_60": "aa026c00bc2de7b40200012d42214250e5e4dbe591069da5e6ede7e6e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e5e6e6e6e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7fd3e93a5e7e7e5e7e7e7e6e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e7e793e2",
    "heat_drain_wte_zero": "aa026c00bc2d18b50200012d42214250191b241a57fd645a19121819181818181818181818181818181818181818181818181818181818181818181818181818181818181818181818181919191a18181818181818181818181818181828156f5a18181a1818181918181818181818181818181818181818181818181fdd",
    "heat_drain_on": "aa026c00bc2d2fb50200012d422142502e2c132de488526d2e252f2e2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2e2e2e2e2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f1f22586d2f2f2d2f2f2f2e2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2f2fa354",
    "heat_drain_off_drain_free": "aa026c00bc2d66b50200012d4221425067655a6486c91b24676c6667666666666666666666666666666666666666666666666666666666666666666666666666666666666666666666656767676666666666666666666666666666666663da10246666646666666766666666666666666666666666666666666666668151",
    "heat_fahrenheit_standby": "aa026c00bc2da5b50200012d42214250a4a699a7e7dcdbe7a4afa5a4a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a7a4a7a4a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5550bd2e7a5a5a7a5a5a5a4a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5a5f338",
}


@pytest.fixture
def packet_sequence():
    return list(PACKETS.values())


@pytest.fixture
def device(mocker: MockerFixture):
    ble_dev = mocker.Mock()
    ble_dev.address = "AA:BB:CC:DD:EE:FF"
    adv_data = mocker.MagicMock()
    device = Device(ble_dev, adv_data, "KT21TEST1234")
    device._conn = mocker.AsyncMock()
    return device


async def _process(device: Device, hex_packet: str) -> bool:
    packet = await device.packet_parse(bytes.fromhex(hex_packet))
    assert packet is not None
    return await device.data_parse(packet)


def _sent_drain_payload(device: Device) -> bytes:
    packet = device._conn.send_packet.call_args.args[0]
    assert packet.cmd_id == 0x59
    return packet.payload


async def test_wave2_parses_all_packets_successfully(device, packet_sequence):
    for i, hex_packet in enumerate(packet_sequence):
        packet = await device.packet_parse(bytes.fromhex(hex_packet))

        assert packet is not None, f"Packet {i} failed to parse"
        assert packet.src == 0x42, f"Packet {i} has unexpected src: {packet.src:#04x}"
        assert packet.cmd_set == 0x42, (
            f"Packet {i} has unexpected cmd_set: {packet.cmd_set:#04x}"
        )
        assert packet.cmd_id == 0x50, (
            f"Packet {i} has unexpected cmd_id: {packet.cmd_id:#04x}"
        )


async def test_wave2_processes_all_packets_successfully(device, packet_sequence):
    for i, hex_packet in enumerate(packet_sequence):
        processed = await _process(device, hex_packet)
        assert processed is True, f"Packet {i} was not processed"


async def test_wave2_exact_values_from_known_packets(device, packet_sequence):
    for hex_packet in packet_sequence:
        await _process(device, hex_packet)

    expected = {
        Device.main_mode: MainMode.WARM,
        Device.sub_mode: SubMode.NORMAL,
        Device.fan_speed: FanGear.HIGH,
        Device.power_mode: PowerMode.STANDBY,
        Device.power: False,
        Device.target_temperature: 60,
        Device.temp_unit: units.Temperature.F,
        Device.target_temperature_min: 60,
        Device.target_temperature_max: 86,
        Device.ambient_temperature: 63.62,
        Device.outlet_temperature: 61.92,
        Device.wte_fth_en: 2,
        Device.automatic_drain: False,
        Device.drain_mode: DrainMode.EXTERNAL,
        Device.water_level: WaterLevel.LOW,
        Device.ambient_light: False,
        Device.battery_level: 0,
        Device.power_battery: 0,
        Device.power_psdr: 0,
        Device.power_mppt: 0,
    }

    for field_name, expected_value in expected.items():
        actual_value = device.get_value(field_name)
        assert actual_value == expected_value, (
            f"{field_name}: expected {expected_value}, got {actual_value}"
        )


@pytest.mark.parametrize(
    ("packet_name", "expected_unit", "expected_min", "expected_max", "expected_temp"),
    [
        ("heat_celsius_target_16", units.Temperature.C, 16, 30, 16),
        ("heat_celsius_target_30", units.Temperature.C, 16, 30, 30),
        ("fan_fahrenheit_target_60", units.Temperature.F, 60, 86, 60),
        ("heat_fahrenheit_target_86", units.Temperature.F, 60, 86, 86),
    ],
)
async def test_temperature_unit_and_limits_follow_device_temp_sys(
    device, packet_name, expected_unit, expected_min, expected_max, expected_temp
):
    await _process(device, PACKETS[packet_name])

    assert device.temp_unit is expected_unit
    assert device.target_temperature_min == expected_min
    assert device.target_temperature_max == expected_max
    assert device.target_temperature == expected_temp


@pytest.mark.parametrize(
    ("packet_name", "expected_mode"),
    [
        ("fan_celsius_target_30", MainMode.FAN),
        ("heat_celsius_target_30", MainMode.WARM),
    ],
)
async def test_main_mode_is_decoded_from_heartbeat(device, packet_name, expected_mode):
    await _process(device, PACKETS[packet_name])

    assert device.main_mode is expected_mode


@pytest.mark.parametrize(
    ("packet_name", "expected_auto"),
    [
        # in Heat mode only wte_fth_en == 1 means auto drain is active
        ("heat_drain_wte_zero", False),
        ("heat_drain_on", True),
        ("heat_drain_off_external", False),
        ("heat_drain_off_drain_free", False),
    ],
)
async def test_heat_mode_drain_state_is_decoded_from_wte_fth_en(
    device, packet_name, expected_auto
):
    await _process(device, PACKETS[packet_name])

    assert device.automatic_drain is expected_auto
    assert device.drain_mode is DrainMode.EXTERNAL


def test_drain_state_is_unknown_before_first_heartbeat(device):
    assert device.automatic_drain is None
    assert device.drain_mode is None


@pytest.mark.parametrize(
    ("packet_name", "enabled", "expected_payload"),
    [
        # drain-free is unsupported in Heat/Fan; enabling always sends 1 and
        # disabling preserves the drain-mode preference bit
        ("heat_drain_wte_zero", True, 1),
        ("heat_drain_off_external", True, 1),
        ("heat_drain_on", False, 3),
        ("fan_fahrenheit_target_60", True, 1),
    ],
)
async def test_enable_automatic_drain_outside_cool_mode(
    device, packet_name, enabled, expected_payload
):
    await _process(device, PACKETS[packet_name])

    await device.enable_automatic_drain(enabled)

    assert _sent_drain_payload(device) == expected_payload.to_bytes()


# No Cool-mode heartbeats exist in the available captures, so Cool-mode drain
# behavior is exercised by setting the decoded fields directly.
def _force_cool_mode(device: Device, wte_fth_en: int):
    device.main_mode = MainMode.COLD.value
    device.wte_fth_en = wte_fth_en


@pytest.mark.parametrize(
    ("wte_fth_en", "expected_auto", "expected_mode"),
    [
        (0, True, DrainMode.EXTERNAL),
        (1, True, DrainMode.DRAIN_FREE),
        (2, False, DrainMode.EXTERNAL),
        (3, False, DrainMode.DRAIN_FREE),
    ],
)
def test_cool_mode_drain_state_is_decoded_from_wte_fth_en(
    device, wte_fth_en, expected_auto, expected_mode
):
    _force_cool_mode(device, wte_fth_en)

    assert device.automatic_drain is expected_auto
    assert device.drain_mode is expected_mode


@pytest.mark.parametrize(
    ("wte_fth_en", "enabled", "expected_payload"),
    [
        (2, True, 0),
        (3, True, 1),
        (0, False, 2),
        (1, False, 3),
    ],
)
async def test_enable_automatic_drain_in_cool_mode_preserves_preference(
    device, wte_fth_en, enabled, expected_payload
):
    _force_cool_mode(device, wte_fth_en)

    await device.enable_automatic_drain(enabled)

    assert _sent_drain_payload(device) == expected_payload.to_bytes()


@pytest.mark.parametrize(
    ("wte_fth_en", "mode", "expected_payload"),
    [
        (0, DrainMode.DRAIN_FREE, 1),
        (1, DrainMode.EXTERNAL, 0),
        # with auto drain off only the preference bit is stored
        (2, DrainMode.DRAIN_FREE, 3),
        (3, DrainMode.EXTERNAL, 2),
    ],
)
async def test_set_drain_mode_in_cool_mode_sends_new_wte_value(
    device, wte_fth_en, mode, expected_payload
):
    _force_cool_mode(device, wte_fth_en)

    await device.set_drain_mode(mode)

    assert _sent_drain_payload(device) == expected_payload.to_bytes()


@pytest.mark.parametrize("packet_name", ["heat_drain_on", "fan_fahrenheit_target_60"])
@pytest.mark.parametrize("mode", [DrainMode.DRAIN_FREE, DrainMode.EXTERNAL])
async def test_set_drain_mode_is_a_noop_outside_cool_mode(device, packet_name, mode):
    await _process(device, PACKETS[packet_name])
    device._conn.send_packet.reset_mock()

    await device.set_drain_mode(mode)

    device._conn.send_packet.assert_not_called()


def test_power_mode_select_hides_internal_init_state(device):
    """
    INIT is folded into the dynamic exclude (with OFF) rather than the static list,
    so options_str carries the full enum and INIT is only actually hidden once the
    dynamic exclusion is applied at the entity layer - checked here at the source.
    """
    assert PowerMode.INIT in device._power_mode_excluded_options


def _drain_switch(device: Device):
    return next(
        c
        for c in device.get_controls(control_type=controls.switch)
        if c.key == "automatic_drain"
    )


def _drain_select(device: Device):
    return next(
        c
        for c in device.get_controls(control_type=controls.select)
        if c.key == "drain_mode"
    )


def _power_mode_select(device: Device):
    return next(
        c
        for c in device.get_controls(control_type=controls.select)
        if c.key == "power_mode"
    )


async def test_automatic_drain_switch_is_gated_on_power(device):
    """Toggling the switch while the unit is off/standby was silently reverting."""
    assert _drain_switch(device).availability is Device.power

    await _process(device, PACKETS["heat_fahrenheit_standby"])
    assert device.power is False

    await _process(device, PACKETS["heat_drain_on"])
    assert device.power is True


async def test_drain_mode_select_is_gated_on_power_not_main_mode(device):
    """
    Unlike the old whole-select availability, Drain Mode stays available in every
    main mode once the unit is on - only the unsupported *option* is excluded (see
    below) - so it must not also be tied to `main_mode`.
    """
    assert _drain_select(device).availability is Device.power


@pytest.mark.parametrize(
    ("packet_name", "expect_drain_free_excluded"),
    [
        ("heat_drain_on", True),
        ("fan_fahrenheit_target_60", True),
        ("fan_celsius_target_30", True),
    ],
)
async def test_drain_mode_excludes_drain_free_outside_cool_mode(
    device, packet_name, expect_drain_free_excluded
):
    await _process(device, PACKETS[packet_name])

    excluded = device._drain_mode_excluded_options
    assert (DrainMode.DRAIN_FREE in excluded) is expect_drain_free_excluded


def test_drain_mode_does_not_exclude_drain_free_in_cool_mode(device):
    _force_cool_mode(device, wte_fth_en=0)

    assert DrainMode.DRAIN_FREE not in device._drain_mode_excluded_options


@pytest.mark.parametrize(
    "power_src",
    [
        0b00000,  # no source flags at all - not battery-only either
        0b00001,  # AC mains only
        0b10001,  # AC mains + battery also active
        0b00010,  # solar only
        0b00100,  # unverified bit 2 only (possibly a Delta 2/3 over XT150)
        0b10010,  # battery + solar also active
        0b10100,  # battery + unverified bit 2 also active
    ],
)
async def test_power_mode_off_is_excluded_unless_solely_on_battery(
    device, mocker, power_src
):
    """
    Mirrors the app's own DeviceStandbyOrOffPopupWindow gating: Off is only offered
    without hesitation when running solely on battery - every other combination
    (AC mains, solar, the still-unconfirmed bit 2 source, or no source at all)
    excludes it.
    """
    mocker.patch.object(
        Device, "power_src", mocker.PropertyMock(return_value=power_src)
    )

    assert PowerMode.OFF in device._power_mode_excluded_options


@pytest.mark.parametrize(
    "power_src",
    [
        None,
        0b10000,  # battery only, no other source active
    ],
)
async def test_power_mode_off_is_not_excluded_when_solely_on_battery(
    device, mocker, power_src
):
    mocker.patch.object(
        Device, "power_src", mocker.PropertyMock(return_value=power_src)
    )

    assert device._power_mode_excluded_options == [PowerMode.INIT]


def test_power_mode_select_exclude_field_is_wired(device):
    assert _power_mode_select(device).exclude is Device._power_mode_excluded_options


def _ambient_light_switch(device: Device):
    return next(
        c
        for c in device.get_controls(control_type=controls.switch)
        if c.key == "ambient_light"
    )


def _fan_speed_select(device: Device):
    return next(
        c
        for c in device.get_controls(control_type=controls.select)
        if c.key == "fan_speed"
    )


def _main_mode_select(device: Device):
    return next(
        c
        for c in device.get_controls(control_type=controls.select)
        if c.key == "main_mode"
    )


def _sub_mode_select(device: Device):
    return next(
        c
        for c in device.get_controls(control_type=controls.select)
        if c.key == "sub_mode"
    )


def _target_temperature_number(device: Device):
    return next(
        c
        for c in device.get_controls(control_type=controls.temperature)
        if c.key == "target_temperature"
    )


@pytest.mark.parametrize(
    "get_control",
    [
        _ambient_light_switch,
        _fan_speed_select,
        _main_mode_select,
        _sub_mode_select,
        _target_temperature_number,
    ],
)
def test_controls_go_unavailable_in_standby(device, get_control):
    """
    Ambient Light, Fan Speed, Main Mode, Sub Mode and Target Temperature were
    changeable even with the unit off/standby, where the device ignores the change -
    they must now report unavailable instead, matching the drain controls above.
    """
    assert get_control(device).availability is Device.power


async def test_plugged_in_ac_follows_power_src_mains_bit(device, mocker):
    """
    Bit assignments confirmed against real hardware: AC only reads as 1 (bit 0),
    battery only reads as 16 (bit 4), AC + battery reads as 17.
    """
    mocker.patch.object(Device, "power_src", mocker.PropertyMock(return_value=0b00001))
    assert device.plugged_in_ac is True

    mocker.patch.object(Device, "power_src", mocker.PropertyMock(return_value=0b10000))
    assert device.plugged_in_ac is False


def test_plugged_in_ac_is_unknown_before_first_heartbeat(device):
    assert device.plugged_in_ac is None


async def test_battery_connected_follows_power_src_battery_bit(device, mocker):
    mocker.patch.object(Device, "power_src", mocker.PropertyMock(return_value=0b10000))
    assert device.battery_connected is True

    mocker.patch.object(Device, "power_src", mocker.PropertyMock(return_value=0b00001))
    assert device.battery_connected is False


@pytest.mark.parametrize(
    ("power_src", "expected_ac", "expected_battery", "expected_solar"),
    [
        (1, True, False, False),  # AC connected, battery disconnected
        (17, True, True, False),  # AC and battery connected
        (16, False, True, False),  # AC disconnected, battery connected
        (18, False, True, True),  # AC disconnected, battery + solar connected
    ],
)
async def test_power_source_flags_match_real_hardware_readings(
    device, mocker, power_src, expected_ac, expected_battery, expected_solar
):
    mocker.patch.object(
        Device, "power_src", mocker.PropertyMock(return_value=power_src)
    )

    assert device.plugged_in_ac is expected_ac
    assert device.battery_connected is expected_battery
    assert device.solar_connected is expected_solar


def test_battery_connected_is_unknown_before_first_heartbeat(device):
    assert device.battery_connected is None


def test_solar_connected_is_unknown_before_first_heartbeat(device):
    assert device.solar_connected is None
