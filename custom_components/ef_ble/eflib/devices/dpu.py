from enum import IntEnum
from functools import partial

from custom_components.ef_ble.eflib.props.enums import IntFieldValue

from ..commands import TimeCommands
from ..devicebase import AdvertisementData, BLEDevice, DeviceBase
from ..packet import Packet
from ..pb import yj751_sys_pb2
from ..props import (
    Field,
    ProtobufProps,
    field_group,
    pb_field,
    proto_attr_mapper,
    repeated_pb_field_type,
)

pb_heartbeat = proto_attr_mapper(yj751_sys_pb2.AppShowHeartbeatReport)
pb_backend_record_heartbeat = proto_attr_mapper(
    yj751_sys_pb2.BackendRecordHeartbeatReport
)
pb_bp_info = proto_attr_mapper(yj751_sys_pb2.BpInfoReport)
pb_app_para_heartbeat = proto_attr_mapper(yj751_sys_pb2.APPParaHeartbeatReport)
pb_display_property_upload = proto_attr_mapper(yj751_sys_pb2.DisplayPropertyUpload)


class OperatingMode(IntFieldValue):
    NONE = 0
    SELF_POWERED = 1
    SCHEDULED = 2
    TIME_OF_USE = 3


class Access5p8InputType(IntFieldValue):
    IN_IDLE = 0
    IN_AC_EV = 1
    IN_PD303 = 2
    IN_L14_TRANS = 3


class Access5p8OutputType(IntFieldValue):
    OUT_IDLE = 0
    OUT_PARALLEL_BOX = 1
    OUT_PD303 = 2


class SolarSource(IntEnum):
    LV = 0
    HV = 1


class _BatteryLevel(
    repeated_pb_field_type(
        list_field=pb_bp_info.bp_info, value_field=lambda x: x.bp_soc, per_item=True
    )
):
    battery_no: int

    def get_value(self, item: yj751_sys_pb2.BPInfo) -> int | None:
        return item.bp_soc if item.bp_no == self.battery_no else None


class _BatteryTemperature(
    repeated_pb_field_type(
        list_field=pb_bp_info.bp_info, value_field=lambda x: x.bp_temp, per_item=True
    )
):
    battery_no: int

    def get_value(self, item: yj751_sys_pb2.BPInfo) -> int | None:
        return item.bp_temp if item.bp_no == self.battery_no else None


class Device(DeviceBase, ProtobufProps):
    """Delta Pro Ultra"""

    SN_PREFIX = b"Y711"
    NAME_PREFIX = "EF-YJ"

    @staticmethod
    def _has_bit(value: int | None, bit_position: int) -> bool:
        if value is None:
            return False
        return bool((value >> bit_position) & 1)

    @staticmethod
    def _packet_is_addressed(packet: Packet, src: int, cmsSet: int, cmdId: int) -> bool:
        return packet.src == src and packet.cmdSet == cmsSet and packet.cmdId == cmdId

    @staticmethod
    def round2(x: float) -> float:
        return round(x, 2)

    # Bitmap for various binary states and the individual binary states therein
    show_flag = pb_field(pb_heartbeat.show_flag)
    is_charging = pb_field(pb_heartbeat.show_flag, lambda x: Device._has_bit(x, 0))
    dc_ports = pb_field(pb_heartbeat.show_flag, lambda x: Device._has_bit(x, 1))
    slow_charging = pb_field(pb_heartbeat.show_flag, lambda x: Device._has_bit(x, 4))
    ac_allowed = pb_field(pb_heartbeat.show_flag, lambda x: not Device._has_bit(x, 9))
    ac_ports = pb_field(pb_heartbeat.show_flag, lambda x: Device._has_bit(x, 2))
    ac_ports_availability = pb_field(
        pb_heartbeat.show_flag, lambda x: not bool(Device._has_bit(x, 9))
    )

    battery_level = pb_field(pb_heartbeat.soc)

    lv_solar_power = pb_field(pb_heartbeat.in_lv_mppt_pwr, round2)
    lv_solar_voltage = pb_field(pb_backend_record_heartbeat.in_lv_mppt_vol, round2)
    lv_solar_current = pb_field(pb_backend_record_heartbeat.in_lv_mppt_amp, round2)
    lv_solar_temperature = pb_field(pb_backend_record_heartbeat.mppt_lv_temp, round2)
    lv_solar_err_code = pb_field(pb_backend_record_heartbeat.lv_pv_err_code)

    hv_solar_power = pb_field(pb_heartbeat.in_hv_mppt_pwr, round2)
    hv_solar_voltage = pb_field(pb_backend_record_heartbeat.in_hv_mppt_vol, round2)
    hv_solar_current = pb_field(pb_backend_record_heartbeat.in_hv_mppt_amp, round2)
    hv_solar_temperature = pb_field(pb_backend_record_heartbeat.mppt_hv_temp, round2)
    hv_solar_err_code = pb_field(pb_backend_record_heartbeat.hv_pv_err_code)

    ac_5p8_in_power = pb_field(pb_heartbeat.in_ac_5p8_pwr, round2)
    ac_5p8_in_vol = pb_field(pb_backend_record_heartbeat.in_ac_5p8_vol, round2)
    ac_5p8_in_amp = pb_field(pb_backend_record_heartbeat.in_ac_5p8_amp, round2)
    ac_5p8_in_type = pb_field(
        pb_heartbeat.access_5p8_in_type, Access5p8InputType.from_value
    )

    ac_c20_in_power = pb_field(pb_heartbeat.in_ac_c20_pwr, round2)
    ac_c20_in_vol = pb_field(pb_backend_record_heartbeat.in_ac_c20_vol, round2)
    ac_c20_in_amp = pb_field(pb_backend_record_heartbeat.in_ac_c20_amp, round2)
    ac_c20_in_type = pb_field(pb_backend_record_heartbeat.c20_in_type)

    weak_hv_pv = pb_field(
        pb_display_property_upload.plug_in_info_pv_weak_source_flag,
        lambda x: Device._has_bit(x, SolarSource.HV),
    )
    weak_lv_pv = pb_field(
        pb_display_property_upload.plug_in_info_pv_weak_source_flag,
        lambda x: Device._has_bit(x, SolarSource.LV),
    )
    pv_hv_vol_low = pb_field(
        pb_display_property_upload.plug_in_info_pv_vol_low_flag,
        lambda x: Device._has_bit(x, SolarSource.HV),
    )
    pv_lv_vol_low = pb_field(
        pb_display_property_upload.plug_in_info_pv_vol_low_flag,
        lambda x: Device._has_bit(x, SolarSource.LV),
    )

    wireless_4g = pb_field(pb_heartbeat.wireless_4g_on, bool)

    record_flag = pb_field(pb_backend_record_heartbeat.record_flag)
    sys_work_sta = pb_field(pb_backend_record_heartbeat.sys_work_sta)
    chg_reign_sta = pb_field(pb_backend_record_heartbeat.chg_reign_sta)
    fan_state = pb_field(pb_backend_record_heartbeat.fan_state)
    work_5p8_mode = pb_field(pb_backend_record_heartbeat.work_5p8_mode)

    ac_in_freq = pb_field(pb_backend_record_heartbeat.ac_in_freq)
    ac_out_freq = pb_field(pb_backend_record_heartbeat.ac_out_freq)

    ems_work_sta = pb_field(pb_backend_record_heartbeat.ems_work_sta)
    ems_max_avail_num = pb_field(pb_backend_record_heartbeat.ems_max_avail_num)
    ems_open_bms_idx = pb_field(pb_backend_record_heartbeat.ems_open_bms_idx)
    ems_para_vol_min = pb_field(pb_backend_record_heartbeat.ems_para_vol_min)
    ems_para_vol_max = pb_field(pb_backend_record_heartbeat.ems_para_vol_max)

    bat_vol = pb_field(pb_backend_record_heartbeat.bat_vol, round2)
    bat_amp = pb_field(pb_backend_record_heartbeat.bat_amp, round2)

    bms_input_watts = pb_field(pb_backend_record_heartbeat.bms_input_watts, round2)
    bms_output_watts = pb_field(pb_backend_record_heartbeat.bms_output_watts, round2)

    pcs_work_sta = pb_field(pb_backend_record_heartbeat.pcs_work_sta)
    pcs_dc_temp = pb_field(pb_backend_record_heartbeat.pcs_dc_temp, round2)
    pcs_dc_err_code = pb_field(pb_backend_record_heartbeat.pcs_dc_err_code)
    pcs_ac_temp = pb_field(pb_backend_record_heartbeat.pcs_ac_temp, round2)
    pcs_ac_err_code = pb_field(pb_backend_record_heartbeat.pcs_ac_err_code)

    pd_temp = pb_field(pb_backend_record_heartbeat.pd_temp, round2)

    ev_max_charger_cur = pb_field(
        pb_backend_record_heartbeat.ev_max_charger_cur, round2
    )

    input_power = pb_field(pb_heartbeat.watts_in_sum)
    output_power = pb_field(pb_heartbeat.watts_out_sum)

    battery_enabled = field_group(
        lambda _: Field[bool](), 5, name_template="battery_{n}_enabled"
    )
    battery_battery_level = field_group(
        _BatteryLevel, 5, name_template="battery_{n}_battery_level"
    )
    battery_cell_temperature = field_group(
        _BatteryTemperature, 5, name_template="battery_{n}_cell_temperature"
    )

    usb1_out_power = pb_field(pb_heartbeat.out_usb1_pwr)
    usb1_out_vol = pb_field(pb_backend_record_heartbeat.out_usb1_vol, round2)
    usb1_out_amp = pb_field(pb_backend_record_heartbeat.out_usb1_amp, round2)

    usb2_out_power = pb_field(pb_heartbeat.out_usb2_pwr)
    usb2_out_vol = pb_field(pb_backend_record_heartbeat.out_usb2_vol, round2)
    usb2_out_amp = pb_field(pb_backend_record_heartbeat.out_usb2_amp, round2)

    typec1_out_power = pb_field(pb_heartbeat.out_typec1_pwr)
    typec1_out_vol = pb_field(pb_backend_record_heartbeat.out_typec1_vol, round2)
    typec1_out_amp = pb_field(pb_backend_record_heartbeat.out_typec1_amp, round2)

    typec2_out_power = pb_field(pb_heartbeat.out_typec2_pwr)
    typec2_out_vol = pb_field(pb_backend_record_heartbeat.out_typec2_vol, round2)
    typec2_out_amp = pb_field(pb_backend_record_heartbeat.out_typec2_amp, round2)

    ads_out_power = pb_field(pb_heartbeat.out_ads_pwr)
    ads_out_vol = pb_field(pb_backend_record_heartbeat.out_ads_vol, round2)
    ads_out_amp = pb_field(pb_backend_record_heartbeat.out_ads_amp, round2)
    ads_err_code = pb_field(pb_backend_record_heartbeat.ads_err_code)

    ac_l1_1_out_power = pb_field(pb_heartbeat.out_ac_l1_1_pwr)
    ac_l1_1_out_vol = pb_field(pb_backend_record_heartbeat.out_ac_l1_1_vol, round2)
    ac_l1_1_out_amp = pb_field(pb_backend_record_heartbeat.out_ac_l1_1_amp, round2)
    ac_l1_1_out_pf = pb_field(pb_backend_record_heartbeat.out_ac_l1_1_pf, round2)

    ac_l1_2_out_power = pb_field(pb_heartbeat.out_ac_l1_2_pwr)
    ac_l1_2_out_vol = pb_field(pb_backend_record_heartbeat.out_ac_l1_2_vol, round2)
    ac_l1_2_out_amp = pb_field(pb_backend_record_heartbeat.out_ac_l1_2_amp, round2)
    ac_l1_2_out_pf = pb_field(pb_backend_record_heartbeat.out_ac_l1_2_pf, round2)

    ac_l2_1_out_power = pb_field(pb_heartbeat.out_ac_l2_1_pwr)
    ac_l2_1_out_vol = pb_field(pb_backend_record_heartbeat.out_ac_l2_1_vol, round2)
    ac_l2_1_out_amp = pb_field(pb_backend_record_heartbeat.out_ac_l2_1_amp, round2)
    ac_l2_1_out_pf = pb_field(pb_backend_record_heartbeat.out_ac_l2_1_pf, round2)

    ac_l2_2_out_power = pb_field(pb_heartbeat.out_ac_l2_2_pwr)
    ac_l2_2_out_vol = pb_field(pb_backend_record_heartbeat.out_ac_l2_2_vol, round2)
    ac_l2_2_out_amp = pb_field(pb_backend_record_heartbeat.out_ac_l2_2_amp, round2)
    ac_l2_2_out_pf = pb_field(pb_backend_record_heartbeat.out_ac_l2_2_pf, round2)

    ac_tt_out_power = pb_field(pb_heartbeat.out_ac_tt_pwr)
    ac_tt_out_vol = pb_field(pb_backend_record_heartbeat.out_ac_tt_vol, round2)
    ac_tt_out_amp = pb_field(pb_backend_record_heartbeat.out_ac_tt_amp, round2)
    ac_tt_out_pf = pb_field(pb_backend_record_heartbeat.out_ac_tt_pf, round2)

    ac_l14_out_power = pb_field(pb_heartbeat.out_ac_l14_pwr)
    ac_l14_out_vol = pb_field(pb_backend_record_heartbeat.out_ac_l14_vol, round2)
    ac_l14_out_amp = pb_field(pb_backend_record_heartbeat.out_ac_l14_amp, round2)
    ac_l14_out_pf = pb_field(pb_backend_record_heartbeat.out_ac_l14_pf, round2)

    ac_5p8_out_type = pb_field(
        pb_heartbeat.access_5p8_out_type, Access5p8OutputType.from_value
    )
    ac_5p8_out_power = pb_field(pb_heartbeat.out_ac_5p8_pwr)
    ac_5p8_out_vol = pb_field(pb_backend_record_heartbeat.out_ac_5p8_vol, round2)
    ac_5p8_out_amp = pb_field(pb_backend_record_heartbeat.out_ac_5p8_amp, round2)
    ac_5p8_out_pf = pb_field(pb_backend_record_heartbeat.out_ac_5p8_pf, round2)

    backup_discharge_limit = pb_field(pb_app_para_heartbeat.dsg_min_soc)
    backup_discharge_limit_min = 0
    backup_discharge_limit_max = 30

    backup_charge_limit = pb_field(pb_app_para_heartbeat.chg_max_soc)
    backup_charge_limit_min = 50
    backup_charge_limit_max = 100

    backup_reserve_level = pb_field(pb_app_para_heartbeat.sys_backup_soc)
    backup_reserve_level_min = 5
    backup_reserve_level_max = 100

    sys_word_mode = pb_field(
        pb_app_para_heartbeat.sys_word_mode, OperatingMode.from_value
    )

    power_standby_mins = pb_field(pb_app_para_heartbeat.power_standby_mins)

    screen_standby_sec = pb_field(pb_app_para_heartbeat.screen_standby_sec)
    screen_standby_sec_availability = True

    dc_standby_mins = pb_field(pb_app_para_heartbeat.dc_standby_mins)
    dc_standby_mins_availability = True
    ac_standby_mins = pb_field(pb_app_para_heartbeat.ac_standby_mins)

    battery_heating = pb_field(pb_app_para_heartbeat.bms_mode_set, bool)
    solar_only = pb_field(pb_app_para_heartbeat.solar_only_flg, bool)

    ac_xboost = pb_field(pb_app_para_heartbeat.ac_xboost, bool)

    ac_always_on = pb_field(pb_app_para_heartbeat.ac_often_open_flg, bool)

    ac_always_on_soc = pb_field(pb_app_para_heartbeat.ac_often_open_min_soc, int)
    ac_always_on_soc_min = 0
    ac_always_on_soc_max = 100

    chg_5p8_min_charging_power = 600
    chg_5p8_max_charging_power = 7200
    chg_5p8_charging_speed = pb_field(pb_app_para_heartbeat.chg_5p8_set_watts)
    chg_5p8_charging_speed_availability = True

    chg_c20_min_charging_power = 600
    chg_c20_max_charging_power = 1800
    chg_c20_charging_speed = pb_field(pb_app_para_heartbeat.chg_c20_set_watts)
    chg_c20_charging_speed_availability = pb_field(
        pb_heartbeat.show_flag,
        # slow_charging switch enabled
        lambda x: bool(Device._has_bit(x, 4)),
    )

    extra_battery_name = "Delta Pro Ultra Battery"

    @staticmethod
    def check(sn):
        return sn.startswith(Device.SN_PREFIX)

    def __init__(
        self, ble_dev: BLEDevice, adv_data: AdvertisementData, sn: str
    ) -> None:
        super().__init__(ble_dev, adv_data, sn)
        self._time_commands = TimeCommands(self)
        # Add timer to request heartbeat info from backend using update_period
        # with minimum 2 seconds to avoid spamming the device with requests
        self.add_timer_task(
            partial(self.request_heartbeat_info, 8),
            interval=max(2, self._update_period),
        )

    async def packet_parse(self, data: bytes):
        return Packet.fromBytes(data, xor_payload=True)

    async def data_parse(self, packet: Packet) -> bool:
        """Process the incoming notifications from the device"""

        processed = True
        self.reset_updated()

        if Device._packet_is_addressed(packet, 0x02, 0x02, 0x01):
            # Ping
            await self._conn.replyPacket(packet)
            self._logger.debug(
                "%s: %s: Parsed data: %r", self.address, self.name, packet
            )
            self.update_from_bytes(yj751_sys_pb2.AppShowHeartbeatReport, packet.payload)
            # self._logger.debug("DPU AppShowHeartbeatReport: \n %s", str(p))
        elif Device._packet_is_addressed(packet, 0x02, 0x02, 0x02):
            # BackendRecordHeartbeatReport
            await self._conn.replyPacket(packet)
            self.update_from_bytes(
                yj751_sys_pb2.BackendRecordHeartbeatReport, packet.payload
            )
            # self._logger.debug("DPU BackendRecordHeartbeatReport: \n %s", str(p))
        elif Device._packet_is_addressed(packet, 0x02, 0x02, 0x03):
            await self._conn.replyPacket(packet)
            self.update_from_bytes(yj751_sys_pb2.APPParaHeartbeatReport, packet.payload)
            # self._logger.debug("DPU APPParaHeartbeatReport: \n %s", str(p))
        elif Device._packet_is_addressed(packet, 0x02, 0x02, 0x04):
            await self._conn.replyPacket(packet)
            self.update_from_bytes(yj751_sys_pb2.BpInfoReport, packet.payload)
            # self._logger.debug("DPU BpInfoReport: \n %s", str(p))
        elif Device._packet_is_addressed(packet, 0x02, 0x0A, 0x20):
            await self._conn.replyPacket(packet)
            self.update_from_bytes(yj751_sys_pb2.CurrentNode, packet.payload)
            # self._logger.debug("DPU CurrentNode: \n %s", str(p))
            processed = True
        elif Device._packet_is_addressed(packet, 0x02, 0xFE, 0x15):
            await self._conn.replyPacket(packet)
            self.update_from_bytes(yj751_sys_pb2.DisplayPropertyUpload, packet.payload)
            # self._logger.debug("DPU DisplayPropertyUpload: \n %s", str(p))
            processed = True
        elif Device._packet_is_addressed(packet, 0x02, 0x02, 0x17):
            await self._conn.replyPacket(packet)
            self.update_from_bytes(yj751_sys_pb2.DevRequest, packet.payload)
            # self._logger.debug("DPU DevRequest: \n %s", str(p))
        elif Device._packet_is_addressed(packet, 0x35, 0x35, 0x20):
            self._logger.debug(
                "%s: %s: Ping received: %r", self.address, self.name, packet
            )
        elif Device._packet_is_addressed(
            packet, 0x35, 0x01, Packet.NET_BLE_COMMAND_CMD_SET_RET_TIME
        ):
            # Device requested for time and timezone offset, so responding with that
            # otherwise it will not be able to send us predictions and config data
            if len(packet.payload) == 0:
                self._time_commands.async_send_all()
        else:
            self._logger.debug(
                "%s: %s: Unhandled packet: %r", self.address, self.name, packet
            )
            processed = False

        for field_name in self.updated_fields:
            try:
                self.update_callback(field_name)
                self.update_state(field_name, getattr(self, field_name))
            except Exception as e:  # noqa: BLE001
                self._logger.warning(
                    "Error happened while updating field %s: %s", field_name, e
                )

        return processed

    async def _send_command_packet(self, dst: int, cmdFunc: int, cmdId: int, message):
        payload = message.SerializeToString()
        p = Packet(0x21, dst, cmdFunc, cmdId, payload, 0x01, 0x01, 0x13)

        await self._conn.sendPacket(p)

    async def enable_wireless_4g(self, enable: bool):
        """Send command to enable/disable wireless 4G"""

        self._logger.debug("enable_wireless_4g: %s", enable)

        packet = yj751_sys_pb2.Switch4GEnable()
        packet.en_4G_open = 1 if enable else 0

        await self._send_command_packet(53, 53, 117, packet)
        return True

    async def enable_dc_ports(self, enable: bool):
        """Send command to enable/disable DC"""

        self._logger.debug("enable_dc_ports: %s", enable)

        packet = yj751_sys_pb2.DCSwitchSet()
        packet.enable = 1 if enable else 0

        await self._send_command_packet(2, 2, 68, packet)
        return True

    async def enable_ac_ports(self, enable: bool):
        """Send command to enable/disable AC"""

        self._logger.debug("enable_ac_ports: %s", enable)

        if not self.ac_allowed:
            self._logger.warning("Cannot enable AC ports when AC is not allowed")
            return False

        packet = yj751_sys_pb2.ACDsgSet()
        packet.enable = 1 if enable else 0

        await self._send_command_packet(2, 2, 72, packet)
        return True

    async def enable_ac_xboost(self, enable: bool):
        """Send command to enable/disable AC XBoost"""

        self._logger.debug("set_ac_xboost: %s", enable)

        packet = yj751_sys_pb2.ACDsgSet()
        packet.xboost = 1 if enable else 0

        await self._send_command_packet(2, 2, 72, packet)
        return True

    async def enable_battery_heating(self, enable: bool):
        """Send command to enable/disable battery preconditioning"""

        self._logger.debug("enable_battery_heating: %s", enable)

        packet = yj751_sys_pb2.BpHeatSet()
        packet.en_bp_heat = 1 if enable else 0

        await self._send_command_packet(2, 2, 89, packet)
        return True

    async def enable_ac_always_on(self, enable: bool):
        """Send command to enable/disable AC Always On"""

        self._logger.debug(
            "set_ac_always_on: %s, ac_often_open_min_soc: %s",
            enable,
            self.ac_always_on_soc_min,
        )

        packet = yj751_sys_pb2.AcOftenOpenCfg()
        packet.ac_often_open = 1 if enable else 0
        packet.ac_often_open_min_soc = self.ac_always_on_soc_min

        await self._send_command_packet(2, 2, 93, packet)
        return True

    async def unpause_solar(self):
        """Send command to clear weak PV source flag"""

        self._logger.debug("unlock_pv_weak")

        packet = yj751_sys_pb2.ConfigWrite()
        packet.unlock_pv_weak = True

        await self._send_command_packet(2, 2, 89, packet)
        return True

    async def set_ac_always_on_soc_min(self, soc: int):
        """Send command to set AC Always On SOC minimum"""

        self._logger.debug(
            "set_ac_always_on_soc_min: %s, ac_often_open: %s", soc, self.ac_always_on
        )

        packet = yj751_sys_pb2.AcOftenOpenCfg()
        packet.ac_often_open = 1 if self.ac_always_on else 0
        packet.ac_often_open_min_soc = max(
            self.ac_always_on_soc_min, min(soc, self.ac_always_on_soc_max)
        )

        await self._send_command_packet(2, 2, 93, packet)
        return True

    async def set_operating_mode(self, mode: OperatingMode):
        """Send command to set operating mode"""

        self._logger.debug("set_operating_mode: %s", mode)

        packet = yj751_sys_pb2.ConfigWrite()
        cfg = packet.cfg_energy_strategy_operate_mode
        cfg.operate_self_powered_open = mode == OperatingMode.SELF_POWERED
        cfg.operate_scheduled_open = mode == OperatingMode.SCHEDULED
        cfg.operate_tou_mode_open = mode == OperatingMode.TIME_OF_USE

        await self._send_command_packet(2, 254, 17, packet)
        return True

    async def set_chg_c20_charging_speed(self, watts: int):
        """Send command to set C20 charging speed"""

        self._logger.debug("set_chg_c20_charging_speed: %s", watts)

        packet = yj751_sys_pb2.ACChgSet()
        packet.chg_c20_watts = max(
            self.chg_c20_min_charging_power, min(watts, self.chg_c20_max_charging_power)
        )

        await self._send_command_packet(2, 2, 73, packet)
        return True

    async def set_chg_5p8_charging_speed(self, watts: int):
        """Send command to set 5p8 port charging speed"""

        self._logger.debug("set_chg_5p8_charging_speed: %s", watts)

        packet = yj751_sys_pb2.ACChgSet()
        packet.chg_5p8_watts = max(
            self.chg_5p8_min_charging_power, min(watts, self.chg_5p8_max_charging_power)
        )

        await self._send_command_packet(2, 2, 73, packet)
        return True

    async def set_backup_discharge_limit(self, soc: int):
        """Send command to set backup discharge limit"""

        self._logger.debug("set_backup_discharge_limit: %s", soc)

        packet = yj751_sys_pb2.DsgSocMinSet()
        packet.min_dsg_soc = max(
            self.backup_discharge_limit_min, min(soc, self.backup_discharge_limit_max)
        )

        await self._send_command_packet(2, 2, 88, packet)
        return True

    async def set_backup_charge_limit(self, soc: int):
        """Send command to set backup charge limit"""

        self._logger.debug("set_backup_charge_limit: %s", soc)

        packet = yj751_sys_pb2.ChgSocMaxSet()
        packet.max_chg_soc = max(
            self.backup_charge_limit_min, min(soc, self.backup_charge_limit_max)
        )

        await self._send_command_packet(2, 2, 87, packet)
        return True

    async def set_backup_reserve_level(self, soc: int):
        """Send command to set backup reserve level"""

        self._logger.debug("set_backup_reserve_level: %s", soc)

        packet = yj751_sys_pb2.ConfigWrite()
        packet.cfg_backup_reverse_soc = max(
            self.backup_reserve_level_min, min(soc, self.backup_reserve_level_max)
        )

        await self._send_command_packet(2, 254, 17, packet)
        return True

    async def set_power_standby_mins(self, minutes: int):
        """Send command to set power standby minutes"""

        self._logger.debug("set_power_standby_mins: %s", minutes)

        packet = yj751_sys_pb2.PowerStandbySet()
        packet.power_standby_min = max(0, min(minutes, 1440))

        await self._send_command_packet(2, 2, 81, packet)
        return True

    async def set_screen_standby_sec(self, seconds: int):
        """Send command to set LCD standby seconds"""

        self._logger.debug("set_screen_standby_sec: %s", seconds)

        packet = yj751_sys_pb2.ScreenStandbySet()
        packet.screen_standby_sec = max(0, min(seconds, 1800))

        await self._send_command_packet(2, 2, 82, packet)
        return True

    async def set_dc_standby_mins(self, minutes: int):
        """Send command to set DC standby minutes"""

        self._logger.debug("set_dc_standby_mins: %s", minutes)

        packet = yj751_sys_pb2.DCStandbySet()
        packet.dc_standby_min = max(0, min(minutes, 1440))

        await self._send_command_packet(2, 2, 84, packet)
        return True

    async def set_ac_standby_mins(self, minutes: int):
        """Send command to set AC standby minutes"""

        self._logger.debug("set_ac_standby_mins: %s", minutes)

        packet = yj751_sys_pb2.ACStandbySet()
        packet.ac_standby_min = max(0, min(minutes, 1440))

        await self._send_command_packet(2, 2, 83, packet)
        return True

    async def request_heartbeat_info(self, param_type: int):
        """Send command to request heartbeat info"""
        # Report 8 = BackendRecordHeartbeatReport

        self._logger.debug("request_heartbeat_info: %s", param_type)
        packet = yj751_sys_pb2.SystemParamGet()
        packet.get_param_type = param_type

        await self._send_command_packet(2, 2, 103, packet)
        return True
