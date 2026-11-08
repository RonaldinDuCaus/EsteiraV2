from datetime import datetime, timedelta, timezone

import pytest

from backend.app.factory_policy import can_approve, choose_detection, online


NOW = datetime(2026, 11, 8, tzinfo=timezone.utc)


def cycle(**overrides):
    return {"status": "recognized", "completed": False, "device_id": "motor", "boot_id": "boot-A",
            "deadline": NOW + timedelta(seconds=30), **overrides}


def motor(**overrides):
    return {"id": "motor", "boot_id": "boot-A", "authorized": True, **overrides}


def test_approval_requires_current_boot_authorization_and_exact_device():
    assert can_approve(cycle(), motor(), NOW)
    for changed in (motor(authorized=False), motor(boot_id="boot-B"), motor(id="other")):
        assert not can_approve(cycle(), changed, NOW)


@pytest.mark.parametrize("status", ["awaiting_capture", "processing", "unknown", "error", "cancelled"])
def test_only_recognized_can_release(status):
    assert not can_approve(cycle(status=status), motor(), NOW)


def test_expired_or_already_completed_result_never_releases_again():
    assert not can_approve(cycle(deadline=NOW), motor(), NOW)
    assert not can_approve(cycle(completed=True), motor(), NOW)


def test_known_class_is_not_enough_without_active_catalog_mapping():
    detection = [{"class_name": "capacitor", "confidence": 0.95}]
    assert choose_detection(detection, {}, {1: {"name": "Capacitor"}}, 0.8)["status"] == "unknown"
    assert choose_detection(detection, {"capacitor": 1}, {}, 0.8)["status"] == "unknown"
    assert choose_detection(detection, {"capacitor": 1}, {1: {"name": "Capacitor"}}, 0.8)["component_id"] == 1


def test_low_confidence_multiple_objects_and_no_detection_are_rejected():
    components = {1: {"name": "Capacitor"}}
    mapping = {"capacitor": 1}
    item = {"class_name": "capacitor", "confidence": 0.95}
    assert choose_detection([], mapping, components, 0.8)["status"] == "unknown"
    assert choose_detection([item, item], mapping, components, 0.8)["status"] == "unknown"
    assert choose_detection([{**item, "confidence": 0.79}], mapping, components, 0.8)["status"] == "unknown"
    assert choose_detection([{**item, "confidence": float("nan")}], mapping, components, 0.8)["status"] == "error"


def test_online_means_recent_telemetry_not_merely_registered():
    assert not online(None, 5, NOW)
    assert not online({"last_seen": NOW-timedelta(seconds=6)}, 5, NOW)
    assert online({"last_seen": NOW-timedelta(seconds=2)}, 5, NOW)
