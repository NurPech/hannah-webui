"""Synchronous gRPC client for Hannah Core. Flask handles requests synchronously
(no asyncio event loop), so this uses the plain grpc API rather than grpc.aio
like telegram/hannah_telegram/grpc_client.py does."""
from __future__ import annotations

import json
import logging
from typing import Optional

import grpc

from hannah_webui.grpc_interceptors import ProtocolVersionClientInterceptor, read_proto_version
from hannah_proto import hannah_pb2, hannah_pb2_grpc

log = logging.getLogger(__name__)


class HannahClient:
    """Thin synchronous wrapper around the Hannah gRPC stub."""

    def __init__(self, host: str, port: int) -> None:
        self._address = f"{host}:{port}"
        self._channel: Optional[grpc.Channel] = None
        self._stub: Optional[hannah_pb2_grpc.HannahServiceStub] = None

    def connect(self) -> None:
        channel = grpc.insecure_channel(self._address)
        self._channel = grpc.intercept_channel(channel, ProtocolVersionClientInterceptor(read_proto_version()))
        self._stub = hannah_pb2_grpc.HannahServiceStub(self._channel)
        log.info("gRPC channel to Hannah at %s created", self._address)

    def close(self) -> None:
        if self._channel:
            self._channel.close()

    def login(self, username: str, password: str) -> tuple[bool, Optional["hannah_pb2.User"]]:
        """Verifies credentials against Core's user registry. Returns (found, user_or_None).
        grpc.RpcError (Core unreachable) is deliberately not caught here — it would otherwise
        look identical to a wrong password ("Ungültige Zugangsdaten") on the login page.
        Left to propagate to app.py's global grpc.RpcError handler instead."""
        assert self._stub, "call connect() first"
        resp = self._stub.Login(hannah_pb2.LoginRequest(username=username, password=password))
        return resp.found, (resp.user if resp.found else None)

    def get_rooms(self) -> list["hannah_pb2.Room"]:
        assert self._stub, "call connect() first"
        return list(self._stub.GetRooms(hannah_pb2.Empty()).rooms)

    def get_groups(self) -> list["hannah_pb2.Group"]:
        assert self._stub, "call connect() first"
        return list(self._stub.GetGroups(hannah_pb2.Empty()).groups)

    def get_group(self, group_id: str) -> Optional["hannah_pb2.Group"]:
        return next((g for g in self.get_groups() if g.group_id == group_id), None)

    def create_group(self, group_id: str, display_name: str) -> bool:
        assert self._stub, "call connect() first"
        resp = self._stub.CreateGroup(hannah_pb2.CreateGroupRequest(group_id=group_id, display_name=display_name))
        return resp.ok

    def update_group(self, group_id: str, display_name: str) -> bool:
        assert self._stub, "call connect() first"
        resp = self._stub.UpdateGroup(hannah_pb2.UpdateGroupRequest(group_id=group_id, display_name=display_name))
        return resp.ok

    def delete_group(self, group_id: str) -> bool:
        assert self._stub, "call connect() first"
        resp = self._stub.DeleteGroup(hannah_pb2.DeleteGroupRequest(group_id=group_id))
        return resp.ok

    def set_group_rooms(self, group_id: str, room_ids: list[str]) -> bool:
        assert self._stub, "call connect() first"
        resp = self._stub.SetGroupRooms(hannah_pb2.SetGroupRoomsRequest(group_id=group_id, room_ids=room_ids))
        return resp.ok

    def get_satellites(self) -> list["hannah_pb2.Satellite"]:
        assert self._stub, "call connect() first"
        return list(self._stub.GetSatellites(hannah_pb2.Empty()).satellites)

    def set_satellite_room(self, device_id: str, room_id: str, requestor_id: int) -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.SetSatelliteRoom(hannah_pb2.SetSatelliteRoomRequest(device_id=device_id, room_id=room_id, requestor_id=requestor_id))
        return resp.ok, resp.message

    def set_satellite_display_name(self, device_id: str, display_name: str, requestor_id: int) -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.SetSatelliteDisplayName(
            hannah_pb2.SetSatelliteDisplayNameRequest(device_id=device_id, display_name=display_name, requestor_id=requestor_id)
        )
        return resp.ok, resp.message

    def delete_satellite(self, device_id: str, requestor_id: int) -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.DeleteSatellite(
            hannah_pb2.DeleteSatelliteRequest(device_id=device_id, requestor_id=requestor_id)
        )
        return resp.ok, resp.message

    def set_satellite_owner(self, device_id: str, user_id: int, requestor_id: int) -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.SetSatelliteOwner(hannah_pb2.SetSatelliteOwnerRequest(device_id=device_id, user_id=user_id, requestor_id=requestor_id))
        return resp.ok, resp.message

    def get_settings(self) -> tuple[list["hannah_pb2.Category"], list["hannah_pb2.Setting"]]:
        assert self._stub, "call connect() first"
        resp = self._stub.GetSettings(hannah_pb2.Empty())
        return list(resp.categories), list(resp.settings)

    def update_setting(self, setting_id: int, value_json: str) -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.UpdateConfig(hannah_pb2.UpdateConfigRequest(
            updates=[hannah_pb2.SettingUpdate(setting_id=setting_id, value=value_json)]
        ))
        return resp.ok, resp.message

    def get_users(self, include_inactive: bool = True) -> list["hannah_pb2.User"]:
        assert self._stub, "call connect() first"
        resp = self._stub.GetUsers(hannah_pb2.GetUsersRequest(include_inactive=include_inactive))
        return list(resp.users)

    def get_residents(self) -> list["hannah_pb2.Resident"]:
        assert self._stub, "call connect() first"
        return list(self._stub.GetResidents(hannah_pb2.Empty()).residents)

    def create_user(self, username: str, password: str, email: str, display_name: str, user_type: str) -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.CreateUser(hannah_pb2.CreateUserRequest(
            username=username, password=password, email=email, display_name=display_name, type=user_type,
        ))
        return resp.ok, resp.message

    def update_user(self, user_id: int, display_name: str, email: str, user_type: str, is_active: bool, password: str = "") -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.UpdateUser(hannah_pb2.UpdateUserRequest(
            user_id=user_id, display_name=display_name, email=email, type=user_type,
            is_active=is_active, password=password,
        ))
        return resp.ok, resp.message

    def delete_user(self, user_id: int) -> bool:
        assert self._stub, "call connect() first"
        resp = self._stub.DeleteUser(hannah_pb2.DeleteUserRequest(user_id=user_id))
        return resp.ok

    def set_trust_level(self, user_id: int, level: int) -> bool:
        assert self._stub, "call connect() first"
        resp = self._stub.SetTrustLevel(hannah_pb2.SetTrustLevelRequest(user_id=user_id, level=level))
        return resp.ok

    def set_system_messages(self, user_id: int, enabled: bool) -> bool:
        assert self._stub, "call connect() first"
        resp = self._stub.SetSystemMessages(hannah_pb2.SetSystemMessagesRequest(user_id=user_id, enabled=enabled))
        return resp.ok

    def link_account(self, user_id: int, service: str, account_id: str, provider_payload: str = "") -> bool:
        assert self._stub, "call connect() first"
        resp = self._stub.LinkAccount(hannah_pb2.LinkAccountRequest(
            user_id=user_id, service=service, account_id=account_id, provider_payload=provider_payload,
        ))
        return resp.ok

    def unlink_account(self, user_id: int, service: str, requestor_id: int) -> bool:
        assert self._stub, "call connect() first"
        resp = self._stub.UnlinkAccount(hannah_pb2.UnlinkAccountRequest(
            user_id=user_id, service=service, requestor_id=requestor_id,
        ))
        return resp.ok

    def get_routines(self) -> list["hannah_pb2.Routine"]:
        assert self._stub, "call connect() first"
        return list(self._stub.GetRoutines(hannah_pb2.Empty()).routines)

    def create_routine(self, name: str, triggers: list[str], actions: list[dict], reply: str) -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.CreateRoutine(hannah_pb2.CreateRoutineRequest(
            name=name, triggers=triggers, actions_json=json.dumps(actions), reply=reply
        ))
        return resp.ok, resp.message

    def update_routine(self, routine_id: int, name: str, triggers: list[str], actions: list[dict], reply: str) -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.UpdateRoutine(hannah_pb2.UpdateRoutineRequest(
            id=routine_id, name=name, triggers=triggers, actions_json=json.dumps(actions), reply=reply
        ))
        return resp.ok, resp.message

    def delete_routine(self, routine_id: int) -> bool:
        assert self._stub, "call connect() first"
        resp = self._stub.DeleteRoutine(hannah_pb2.DeleteRoutineRequest(id=routine_id))
        return resp.ok

    def get_triggers(self) -> list["hannah_pb2.Trigger"]:
        assert self._stub, "call connect() first"
        return list(self._stub.GetTriggers(hannah_pb2.Empty()).triggers)

    def create_trigger(self, trigger_id: str, when, cancel_when, on_response: list, actions: list,
                        say: str, ask: str, rephrase: bool, room: str, cooldown: int, delay: str) -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.CreateTrigger(hannah_pb2.CreateTriggerRequest(
            id=trigger_id, when_json=json.dumps(when), cancel_when_json=json.dumps(cancel_when) if cancel_when else "",
            on_response_json=json.dumps(on_response or []), actions_json=json.dumps(actions or []),
            say=say, ask=ask, rephrase=rephrase, room=room, cooldown=cooldown, delay=delay,
        ))
        return resp.ok, resp.message

    def update_trigger(self, trigger_id: str, when, cancel_when, on_response: list, actions: list,
                        say: str, ask: str, rephrase: bool, room: str, cooldown: int, delay: str) -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.UpdateTrigger(hannah_pb2.UpdateTriggerRequest(
            id=trigger_id, when_json=json.dumps(when), cancel_when_json=json.dumps(cancel_when) if cancel_when else "",
            on_response_json=json.dumps(on_response or []), actions_json=json.dumps(actions or []),
            say=say, ask=ask, rephrase=rephrase, room=room, cooldown=cooldown, delay=delay,
        ))
        return resp.ok, resp.message

    def delete_trigger(self, trigger_id: str) -> bool:
        assert self._stub, "call connect() first"
        resp = self._stub.DeleteTrigger(hannah_pb2.DeleteTriggerRequest(id=trigger_id))
        return resp.ok

    def get_alarms(self, user_id: Optional[int] = None) -> list["hannah_pb2.Alarm"]:
        """GetAlarms returns every alarm — Core has no user_id filter on the RPC — so
        callers scoping to a single user (i.e. /me, where alarms are personal data)
        filter client-side."""
        assert self._stub, "call connect() first"
        alarms = list(self._stub.GetAlarms(hannah_pb2.Empty()).alarms)
        if user_id is not None:
            alarms = [a for a in alarms if a.user_id == user_id]
        return alarms

    def create_alarm(self, satellite_id: str, time: str, weekdays: list[int], one_shot_date: str,
                      label: str, user_id: int) -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.CreateAlarm(hannah_pb2.CreateAlarmRequest(
            satellite_id=satellite_id, time=time, weekdays=weekdays,
            one_shot_date=one_shot_date, label=label, user_id=user_id,
        ))
        return resp.ok, resp.message

    def update_alarm(self, alarm_id: int, satellite_id: str, time: str, weekdays: list[int],
                      skip_dates: list[str], one_shot_date: str, enabled: bool, label: str) -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.UpdateAlarm(hannah_pb2.UpdateAlarmRequest(
            id=alarm_id, satellite_id=satellite_id, time=time, weekdays=weekdays,
            skip_dates=skip_dates, one_shot_date=one_shot_date, enabled=enabled, label=label,
        ))
        return resp.ok, resp.message

    def delete_alarm(self, alarm_id: int) -> bool:
        assert self._stub, "call connect() first"
        resp = self._stub.DeleteAlarm(hannah_pb2.DeleteAlarmRequest(id=alarm_id))
        return resp.ok

    def get_ble_tags(self) -> list["hannah_pb2.BleTag"]:
        assert self._stub, "call connect() first"
        return list(self._stub.GetBleTags(hannah_pb2.Empty()).tags)

    def create_ble_tag(self, mac_address: str, label: str, user_id: int) -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.CreateBleTag(hannah_pb2.CreateBleTagRequest(
            mac_address=mac_address, label=label, user_id=user_id,
        ))
        return resp.ok, resp.message

    def update_ble_tag(self, tag_id: int, mac_address: str, label: str, user_id: int) -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.UpdateBleTag(hannah_pb2.UpdateBleTagRequest(
            id=tag_id, mac_address=mac_address, label=label, user_id=user_id,
        ))
        return resp.ok, resp.message

    def delete_ble_tag(self, tag_id: int) -> bool:
        assert self._stub, "call connect() first"
        resp = self._stub.DeleteBleTag(hannah_pb2.DeleteBleTagRequest(id=tag_id))
        return resp.ok

    def get_cars(self) -> list["hannah_pb2.Car"]:
        assert self._stub, "call connect() first"
        return list(self._stub.GetCars(hannah_pb2.Empty()).cars)

    def create_car(self, topic_prefix: str, home_address: str, owner_user_ids: list[int], name: str = "") -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.CreateCar(hannah_pb2.CreateCarRequest(
            topic_prefix=topic_prefix, home_address=home_address, owner_user_ids=owner_user_ids, name=name,
        ))
        return resp.ok, resp.message

    def update_car(self, car_id: int, topic_prefix: str, home_address: str, owner_user_ids: list[int], name: str = "") -> tuple[bool, str]:
        assert self._stub, "call connect() first"
        resp = self._stub.UpdateCar(hannah_pb2.UpdateCarRequest(
            id=car_id, topic_prefix=topic_prefix, home_address=home_address, owner_user_ids=owner_user_ids, name=name,
        ))
        return resp.ok, resp.message

    def delete_car(self, car_id: int) -> bool:
        assert self._stub, "call connect() first"
        resp = self._stub.DeleteCar(hannah_pb2.DeleteCarRequest(id=car_id))
        return resp.ok
