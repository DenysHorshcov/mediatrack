from app import rawg


def test_rawg_mapping_skips_items_without_id_or_name() -> None:
    assert rawg._map_item({}) is None
    assert rawg._map_item({"id": 1}) is None
    assert rawg._map_item({"name": "No id"}) is None


def test_rawg_mapping_builds_search_item() -> None:
    item = rawg._map_item(
        {
            "id": 3328,
            "name": "The Witcher 3",
            "released": "2015-05-18",
            "background_image": "https://media.rawg.io/w3.jpg",
        }
    )
    assert item is not None
    assert item.id == "3328"
    assert item.type == "game"
    assert item.title == "The Witcher 3"
    assert item.year == 2015
    assert item.poster == "https://media.rawg.io/w3.jpg"


def test_rawg_mapping_handles_missing_year_and_poster() -> None:
    item = rawg._map_item({"id": 1, "name": "Mystery Game"})
    assert item is not None
    assert item.year is None
    assert item.poster is None


def test_rawg_mapping_handles_blank_date() -> None:
    item = rawg._map_item({"id": 1, "name": "Game", "released": ""})
    assert item is not None
    assert item.year is None


def test_rawg_mapping_handles_malformed_date() -> None:
    item = rawg._map_item({"id": 1, "name": "Game", "released": "TBA"})
    assert item is not None
    assert item.year is None
