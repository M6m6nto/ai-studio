from tools.sheets_sync import COLUMNS, item_to_row, rows_from_registry, sync_push


def make_item(**overrides):
    item = {
        "slug": "test-item",
        "codeword": "СЛОВО",
        "updated_at": "2026-08-19T12:00:00+00:00",
        "topic": {
            "source": "instagram", "title": "Тема", "ref_url": "https://example.com/p",
            "ref_account": "some_donor", "ref_post_id": "abc123",
        },
        "script": {"body": "Текст скрипта.", "caption": "Подпись."},
        "ref": {"transcript": "Сырая расшифровка."},
        "steps": {"trend": "done", "ref": "todo", "carousel": "todo", "guide": "todo",
                  "reel": "todo", "funnel": "todo", "deliver": "todo"},
    }
    item.update(overrides)
    return item


def test_item_to_row_matches_column_count():
    row = item_to_row(make_item())
    assert len(row) == len(COLUMNS)


def test_item_to_row_field_order():
    row = item_to_row(make_item())
    assert row[0] == "2026-08-19"           # Дата
    assert row[1] == "instagram"             # Источник
    assert row[2] == "Тема"                  # Название
    assert row[3] == "Текст скрипта."        # Скрипт
    assert row[4] == "Подпись."              # Описание
    assert row[6] == "Сырая расшифровка."    # Исходный скрипт
    assert row[7] == "https://example.com/p"  # Ссылка на исходное видео
    assert row[8] == "some_donor"            # Аккаунт
    assert row[9] == "abc123"                # ID поста


def test_status_done_when_deliver_done():
    item = make_item(steps={"trend": "done", "ref": "done", "carousel": "done", "guide": "done",
                             "reel": "done", "funnel": "done", "deliver": "done"})
    assert item_to_row(item)[5] == "Готово"


def test_status_failed_takes_priority_over_review():
    item = make_item(steps={"trend": "done", "ref": "failed", "carousel": "review", "guide": "todo",
                             "reel": "todo", "funnel": "todo", "deliver": "todo"})
    assert item_to_row(item)[5] == "Ошибка"


def test_status_review_when_something_pending_review():
    item = make_item(steps={"trend": "done", "ref": "review", "carousel": "todo", "guide": "todo",
                             "reel": "todo", "funnel": "todo", "deliver": "todo"})
    assert item_to_row(item)[5] == "На проверке"


def test_status_new_for_fresh_item():
    item = make_item()
    assert item_to_row(item)[5] == "Новый"


def test_rows_from_registry_preserves_order():
    items = [make_item(topic=make_item()["topic"] | {"title": "Раз"}),
             make_item(topic=make_item()["topic"] | {"title": "Два"})]
    rows = rows_from_registry(items)
    assert [r[2] for r in rows] == ["Раз", "Два"]


class FakeSheetsClient:
    def __init__(self):
        self.written = None

    def read_rows(self, sheet_range):
        return []

    def write_rows(self, sheet_range, rows):
        self.written = (sheet_range, rows)


def test_sync_push_writes_all_items():
    client = FakeSheetsClient()
    items = [make_item(), make_item(topic=make_item()["topic"] | {"title": "Другая"})]
    n = sync_push(client, items, "Продакшн!A2:J")
    assert n == 2
    range_written, rows_written = client.written
    assert range_written == "Продакшн!A2:J"
    assert len(rows_written) == 2
