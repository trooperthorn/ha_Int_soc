"""Join attempts parsed from an access point's own log.

The fixtures are real output captured from this estate on 2026-09-10: a U7 Pro
serving the IoT SSID, and an unadopted UDB Pro. Pure functions, no Home
Assistant fixtures needed.
"""
from __future__ import annotations

from custom_components.ha_soc import unifi_ap_log

# Garage-U7Pro, wifi0ap6 (the IoT SSID). Trimmed to the events; the parser is
# given the surrounding noise on purpose.
U7_LOG = """\
Wed Sep  9 20:08:12 2026 user.info hostapd[6944]: wifi0ap6: STA 68:5e:1c:5f:78:dd WPA: authorized
Wed Sep  9 20:08:12 2026 user.info stahtd[6930]: [STA-TRACKER].stahtd_dump_event(): {"op":"event","message_type":"STA_ASSOC_TRACKER","event_type":"association","mac":"68:5e:1c:5f:78:dd","vap":"wifi0ap6","assoc_status":"0","event_id": "1","assoc_delta": "10000","auth_utc": "1789002492.186321","auth_algo": "open","auth_rssi": "-61"}
Wed Sep  9 20:08:12 2026 user.info stahtd[6930]: [STA-TRACKER].stahtd_dump_event(): {"op":"event","message_type":"STA_ASSOC_TRACKER","event_type":"success","mac":"68:5e:1c:5f:78:dd","vap":"wifi0ap6","assoc_status":"0","traffic_delta": "190000","dns_responses": "1","dns_timeouts": "0","ip_delta": "80000","ip_assign_type": "dhcp","wpa_auth_delta": "70000","assoc_delta": "10000","auth_delta": "0","event_id": "2","auth_ts": "3826581.584441","auth_utc": "1789002492.186321","dns_resp_seen": "yes","auth_rssi": "-61","auth_algo": "open"}
Wed Sep  9 20:08:13 2026 user.info stahtd[6930]: [STA-TRACKER].stahtd_dump_event(): {"op":"event","message_type":"STA_ASSOC_TRACKER","event_type":"sta_leave","mac":"68:5e:1c:5f:78:dd","vap":"wifi0ap6","assoc_status":"0","event_id": "2","sta_dc_reason": "sta left","deauth_reason": "1","avg_rssi": "-66"}
Wed Sep  9 20:08:14 2026 user.info stahtd[6930]: [STA-TRACKER].stahtd_dump_event(): {"op":"event","message_type":"STA_ASSOC_TRACKER","event_type":"soft failure","mac":"9c:65:f9:48:d2:28","vap":"wifi0ap6","assoc_status":"0","ip_assign_type": "roamed","wpa_auth_delta": "130000","assoc_delta": "60000","auth_delta": "0","event_id": "482","auth_ts": "3826568.412971","auth_utc": "1789002479.014444","sta_dc_reason": "sta left","disassoc_reason": "8","avg_rssi": "-66","auth_rssi": "-63","auth_algo": "open"}
Wed Sep  9 20:08:28 2026 user.info stahtd[6930]: [STA-TRACKER].stahtd_dump_event(): {"op":"event","message_type":"STA_ASSOC_TRACKER","event_type":"failure","mac":"c4:5b:be:6a:fe:6f","vap":"wifi0ap6","assoc_status":"0","wpa_auth_failures": "1","assoc_delta": "10000","auth_delta": "0","event_id": "17","auth_ts": "3826582.442799","auth_utc": "1789002493.044705","avg_rssi": "-78","auth_rssi": "-74","auth_algo": "open"}
Wed Sep  9 20:08:59 2026 user.info stahtd[6930]: [STA-TRACKER].stahtd_dump_event(): {"op":"event","message_type":"STA_ASSOC_TRACKER","event_type":"failure","mac":"a4:e5:7c:da:e6:a4","vap":"wifi0ap6","assoc_status":"0","auth_failures": "1","event_id": "3","auth_ts": "3826613.128521","auth_utc": "1789002523.731374","sta_dc_reason": "sta left","auth_rssi": "-74","auth_algo": "open"}
Wed Sep  9 20:09:19 2026 user.info stahtd[6930]: [STA-TRACKER].stahtd_dump_event(): {"op":"event","message_type":"STA_ASSOC_TRACKER","event_type":"failure","mac":"a4:e5:7c:da:e6:a4","vap":"wifi0ap6","assoc_status":"0","auth_failures": "1","event_id": "4","auth_ts": "3826633.820048","auth_utc": "1789002544.423540","auth_rssi": "-73","auth_algo": "open"}
"""

# UDBPro-v1.5.1, unadopted: no wireless events at all.
UDB_LOG = """\
Apr 16 05:47:18 syslog: mcad[841]: ace_reporter.reporter_fail(): Unable to resolve (http://unifi:8080/inform)
Apr 16 05:47:18 syslog: mcad[841]: ace_reporter.reporter_fail(): inform failed #2 (last inform: unknown), rc=1
Apr 16 05:47:20 syswrapper: do_update_uplink_by_gw: gateway not reachable, deferring
Apr 16 05:56:06 dropbear[2097]: Login attempt for nonexistent user from 10.30.30.102:51463
"""


def _by_mac(rows):
    return {r["mac"]: r for r in rows}


def test_the_two_failure_modes_are_told_apart() -> None:
    """A client failing 802.11 auth and one failing the WPA handshake both
    arrive as event_type "failure"; they are different problems."""
    clients = _by_mac(unifi_ap_log.analyze(U7_LOG)["clients"])

    wpa = clients["c4:5b:be:6a:fe:6f"]
    assert wpa["last_stage"] == unifi_ap_log.STAGE_WPA
    assert wpa["wpa_auth_failures"] == 1
    assert wpa["auth_failures"] == 0
    assert wpa["worst_rssi"] == -78

    auth = clients["a4:e5:7c:da:e6:a4"]
    assert auth["last_stage"] == unifi_ap_log.STAGE_AUTH
    assert auth["auth_failures"] == 2  # two attempts, one counter each
    assert auth["wpa_auth_failures"] == 0
    assert auth["attempts"] == 2


def test_a_client_that_got_on_is_not_reported_as_failing() -> None:
    row = _by_mac(unifi_ap_log.analyze(U7_LOG)["clients"])["68:5e:1c:5f:78:dd"]
    assert row["ever_succeeded"] is True
    assert row["failures"] == 0
    # It left afterwards; leaving is not a refusal.
    assert row["last_outcome"] == unifi_ap_log.OUTCOME_LEFT
    assert row["last_reason_code"] == 1


def test_a_roam_is_a_soft_failure_with_its_reason_named() -> None:
    row = _by_mac(unifi_ap_log.analyze(U7_LOG)["clients"])["9c:65:f9:48:d2:28"]
    assert row["last_outcome"] == unifi_ap_log.OUTCOME_SOFT
    assert row["failures"] == 0
    assert row["last_reason_code"] == 8
    assert row["last_reason"] == "Disassociated because the client is leaving the BSS"


def test_clients_that_never_got_on_sort_first() -> None:
    rows = unifi_ap_log.analyze(U7_LOG)["clients"]
    failing = [r["mac"] for r in rows if r["failures"] and not r["ever_succeeded"]]
    assert [r["mac"] for r in rows][: len(failing)] == failing
    # The two-failure client outranks the one-failure client.
    assert rows[0]["mac"] == "a4:e5:7c:da:e6:a4"


def test_the_tracker_clock_is_preferred_over_the_syslog_prefix() -> None:
    """A device that cannot reach the controller cannot reach NTP either."""
    events = unifi_ap_log.parse_log(U7_LOG)["events"]
    assert events[0]["at"] == 1789002492.186321


def test_an_unadopted_device_reports_no_activity_not_no_failures() -> None:
    """The whole point: silence is not a pass."""
    result = unifi_ap_log.analyze(UDB_LOG)
    assert result["events"] == []
    assert result["clients"] == []
    assert result["wireless_activity"] is False
    assert result["controller_unreachable"] is True
    assert result["inform_failures"] == 2


def test_a_healthy_log_is_not_flagged_as_unreachable() -> None:
    result = unifi_ap_log.analyze(U7_LOG)
    assert result["wireless_activity"] is True
    assert result["controller_unreachable"] is False


def test_hostapd_lines_alone_still_count_as_wireless_activity() -> None:
    """Firmware without the tracker must not look like an unadopted device."""
    only_hostapd = (
        "Wed Sep  9 20:08:12 2026 user.info hostapd[6944]: "
        "wifi0ap6: STA 68:5e:1c:5f:78:dd IEEE 802.11: authenticated\n"
    )
    result = unifi_ap_log.analyze(only_hostapd)
    assert result["wireless_activity"] is True
    assert result["hostapd_station_lines"] == 1
    assert result["clients"] == []


def test_a_truncated_final_line_does_not_discard_the_excerpt() -> None:
    """A tail can cut mid-JSON; the rest of the excerpt is still good."""
    text = U7_LOG + 'stahtd_dump_event(): {"op":"event","mac":"aa:bb:cc'
    assert len(unifi_ap_log.analyze(text)["events"]) == 7


def test_an_unmapped_reason_code_is_not_given_invented_prose() -> None:
    assert unifi_ap_log.reason_text(8) == "Disassociated because the client is leaving the BSS"
    assert unifi_ap_log.reason_text(200) is None
    assert unifi_ap_log.reason_text(None) is None


def test_a_failure_with_no_counter_set_does_not_name_a_stage() -> None:
    line = (
        'stahtd_dump_event(): {"message_type":"STA_ASSOC_TRACKER","event_type":"failure",'
        '"mac":"aa:bb:cc:dd:ee:ff","vap":"wifi0ap6"}'
    )
    (event,) = unifi_ap_log.parse_log(line)["events"]
    assert event["outcome"] == unifi_ap_log.OUTCOME_FAILURE
    assert event["stage"] == "unknown"
