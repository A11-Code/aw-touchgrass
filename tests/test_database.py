import database


def test_warning_log_round_trip(tmp_path):
    db_path = tmp_path / "warnings.sqlite3"
    log_id = database.insert_log("Code", 121.5, 1, db_path)

    logs = database.get_recent_logs(database_path=db_path)

    assert logs[0]["id"] == log_id
    assert logs[0]["trigger_app"] == "Code"
    assert logs[0]["resolved"] == 0
    database.resolve_logs(db_path)
    assert database.get_recent_logs(database_path=db_path)[0]["resolved"] == 1


def test_audit_event_is_returned_with_event_type(tmp_path):
    db_path = tmp_path / "events.sqlite3"
    database.insert_log(
        "Grass proof accepted",
        0,
        2,
        db_path,
        event_type="proof_accepted",
        resolved=True,
    )

    event = database.get_recent_logs(database_path=db_path)[0]

    assert event["event_type"] == "proof_accepted"
    assert event["resolved"] == 1
