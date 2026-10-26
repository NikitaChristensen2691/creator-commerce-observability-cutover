from src.creator_service import DeliveryRequest, decide_delivery


def test_empty_asset_stays_in_processing_and_does_not_notify_subscriber():
    decision = decide_delivery(DeliveryRequest("sub-8", "clip-4", "audio", 0))

    assert decision.state == "processing"
    assert decision.event == "asset_waiting"


def test_processed_asset_creates_the_subscriber_update_decision():
    decision = decide_delivery(DeliveryRequest("sub-8", "clip-4", "audio", 2048))

    assert decision == type(decision)("ready", "subscriber_update")

