import pytest
from unittest.mock import MagicMock, patch
from src.qdrant_client import search_collection, filter_and_search_schemes


def test_search_collection_returns_results():
    mock_client = MagicMock()
    mock_point = MagicMock()
    mock_point.payload = {"id": "pm-kisan", "name": "PM-KISAN", "description": "farmer support"}
    mock_point.score = 0.85
    mock_client.query_points.return_value.points = [mock_point]

    with patch("src.qdrant_client._get_client", return_value=mock_client):
        results = search_collection(
            collection_name="schemes",
            query_text="farmer income support",
            limit=3
        )
    assert len(results) == 1
    assert results[0]["id"] == "pm-kisan"
    assert results[0]["score"] == 0.85


def test_filter_and_search_schemes_applies_filters():
    mock_client = MagicMock()
    mock_point = MagicMock()
    mock_point.payload = {
        "id": "pm-kisan",
        "name": "PM-KISAN",
        "eligibility": {"occupation": ["farmer"], "land_max_acres": 5}
    }
    mock_point.score = 0.9
    mock_client.query_points.return_value.points = [mock_point]

    with patch("src.qdrant_client._get_client", return_value=mock_client):
        results = filter_and_search_schemes(
            query_text="kisan yojana",
            occupation="farmer",
            land_acres=2.0,
            limit=3
        )

    # Verify filter was passed to query_points
    call_kwargs = mock_client.query_points.call_args
    assert call_kwargs is not None
    query_filter = call_kwargs.kwargs.get("query_filter") or call_kwargs[1].get("query_filter")
    assert query_filter is not None, "Filter should have been passed to query_points"
