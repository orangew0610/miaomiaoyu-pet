from datetime import datetime, timezone

from debugpet.services.reminders import ReminderService


def test_single_reminder_is_claimed_once_and_kept_for_completion(tmp_path):
    service = ReminderService(tmp_path / "reminders.sqlite3")
    due = datetime(2026, 11, 27, 10, 40, tzinfo=timezone.utc)
    reminder = service.create("睡觉", due, "once")

    claimed = service.claim_due(datetime(2026, 11, 27, 10, 41, tzinfo=timezone.utc))

    assert [item.id for item in claimed] == [reminder.id]
    assert service.claim_due(datetime(2026, 11, 27, 11, 0, tzinfo=timezone.utc)) == []
    stored = service.list_all()[0]
    assert not stored.enabled
    assert not stored.completed
    assert stored.last_triggered_at is not None


def test_daily_and_weekday_reminders_advance_deterministically(tmp_path):
    service = ReminderService(tmp_path / "reminders.sqlite3")
    friday = datetime(2026, 11, 27, 9, 0, tzinfo=timezone.utc)
    service.create("每日提醒", friday, "daily")
    service.create("工作日打卡", friday, "weekdays")
    now = datetime(2026, 11, 27, 10, 0, tzinfo=timezone.utc)

    assert len(service.claim_due(now)) == 2
    reminders = {item.title: item for item in service.list_all()}

    assert reminders["每日提醒"].due_at == datetime(
        2026, 11, 28, 9, 0, tzinfo=timezone.utc
    )
    assert reminders["工作日打卡"].due_at == datetime(
        2026, 11, 30, 9, 0, tzinfo=timezone.utc
    )


def test_reminders_persist_and_support_management_actions(tmp_path):
    database = tmp_path / "reminders.sqlite3"
    service = ReminderService(database)
    reminder = service.create(
        "提交周报", datetime(2026, 12, 4, 9, 0, tzinfo=timezone.utc), "weekly"
    )

    reopened = ReminderService(database)
    assert reopened.list_all()[0].title == "提交周报"
    assert reopened.set_enabled(reminder.id, False)
    assert not reopened.list_all()[0].enabled
    assert reopened.complete(reminder.id)
    assert reopened.list_all()[0].completed
    assert reopened.delete(reminder.id)
    assert reopened.list_all() == []


def test_weekend_and_custom_weekdays_advance_to_selected_days(tmp_path):
    service = ReminderService(tmp_path / "reminders.sqlite3")
    friday = datetime(2026, 11, 27, 9, 0, tzinfo=timezone.utc)
    weekend = service.create("周末提醒", friday, "weekends")
    custom = service.create("周二周四", friday, "custom", repeat_days=(1, 3))

    assert weekend.due_at == datetime(2026, 11, 28, 9, 0, tzinfo=timezone.utc)
    assert custom.due_at == datetime(2026, 12, 1, 9, 0, tzinfo=timezone.utc)
    assert service.claim_due(datetime(2026, 11, 27, 10, 0, tzinfo=timezone.utc)) == []

    service.claim_due(datetime(2026, 12, 1, 10, 0, tzinfo=timezone.utc))
    reminders = {item.title: item for item in service.list_all()}

    assert reminders["周二周四"].due_at == datetime(
        2026, 12, 3, 9, 0, tzinfo=timezone.utc
    )
    assert reminders["周二周四"].repeat_days == (1, 3)
    assert custom.repeat_days == (1, 3)


def test_monthly_and_yearly_schedules_clamp_short_months(tmp_path):
    service = ReminderService(tmp_path / "reminders.sqlite3")
    service.create(
        "月末提醒", datetime(2027, 1, 31, 9, 0, tzinfo=timezone.utc), "monthly"
    )
    service.create(
        "周年提醒", datetime(2028, 2, 29, 9, 0, tzinfo=timezone.utc), "yearly"
    )

    service.claim_due(datetime(2027, 1, 31, 10, 0, tzinfo=timezone.utc))
    monthly = {item.title: item for item in service.list_all()}["月末提醒"]
    assert monthly.due_at == datetime(2027, 2, 28, 9, 0, tzinfo=timezone.utc)

    service.claim_due(datetime(2028, 2, 29, 10, 0, tzinfo=timezone.utc))
    yearly = {item.title: item for item in service.list_all()}["周年提醒"]
    assert yearly.due_at == datetime(2029, 2, 28, 9, 0, tzinfo=timezone.utc)


def test_custom_recurrence_requires_at_least_one_weekday(tmp_path):
    service = ReminderService(tmp_path / "reminders.sqlite3")

    try:
        service.create(
            "无星期", datetime(2026, 11, 27, 9, 0, tzinfo=timezone.utc), "custom"
        )
    except ValueError as error:
        assert "at least one weekday" in str(error)
    else:
        raise AssertionError("custom recurrence accepted without weekdays")
