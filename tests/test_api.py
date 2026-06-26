from src.db.models import CalculationHistory

def test_calculate_endpoint_success(api_client, db_session):
    # Post calculation
    payload = {
        "expression": "sin(x) * 10",
        "variables": {"x": 1.570796}
    }
    response = api_client.post("/calculate", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["expression"] == "sin(x) * 10"
    assert data["variables"] == {"x": 1.570796}
    assert round(data["result"], 1) == 10.0
    assert data["execution_time_ms"] >= 0.0
    assert data["cached"] is False

    # Verify database has the record
    records = db_session.query(CalculationHistory).all()
    assert len(records) == 1
    assert records[0].expression == "sin(x) * 10"
    assert records[0].result is not None
    assert round(records[0].result, 1) == 10.0
    assert records[0].error is None

def test_calculate_endpoint_error(api_client, db_session):
    # Post invalid expression
    payload = {
        "expression": "10 / (5 - 5)",
        "variables": {}
    }
    response = api_client.post("/calculate", json=payload)

    # Should raise HTTP 400 Bad Request
    assert response.status_code == 400
    data = response.json()
    assert "division by zero" in data["detail"].lower()

    # Verify that the database STILL saved the calculation with the error message
    records = db_session.query(CalculationHistory).all()
    assert len(records) == 1
    assert records[0].expression == "10 / (5 - 5)"
    assert records[0].result is None
    assert "division by zero" in records[0].error.lower()

def test_history_endpoint(api_client):
    # Perform calculations
    api_client.post("/calculate", json={"expression": "1 + 1"})
    api_client.post("/calculate", json={"expression": "2 + 2"})
    api_client.post("/calculate", json={"expression": "1 + 1"})

    # Fetch history
    res_all = api_client.get("/history")
    assert res_all.status_code == 200
    history = res_all.json()
    assert len(history) == 3

    # Check order (recent first)
    assert history[0]["expression"] == "1 + 1"
    assert history[1]["expression"] == "2 + 2"

    # Fetch history with limit
    res_limit = api_client.get("/history?limit=1")
    assert res_limit.status_code == 200
    assert len(res_limit.json()) == 1

    # Fetch history filtered by expression
    res_filter = api_client.get("/history?expression=2%20%2B%202")
    assert res_filter.status_code == 200
    filtered = res_filter.json()
    assert len(filtered) == 1
    assert filtered[0]["expression"] == "2 + 2"

def test_stats_endpoint(api_client):
    # Perform some calculations (one success, one error)
    api_client.post("/calculate", json={"expression": "5 * 5"})
    api_client.post("/calculate", json={"expression": "log(0)"})  # Will error

    # Fetch stats
    response = api_client.get("/stats")
    assert response.status_code == 200
    stats = response.json()

    # DB Stats merged fields
    assert stats["total"] == 2
    assert stats["error_rate"] == 0.5
    assert stats["avg_time"] >= 0.0

    # Service Stats merged fields
    assert "total_operations_performed" in stats
    assert "precision_digits" in stats
    assert "cache_hits" in stats
