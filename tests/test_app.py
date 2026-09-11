from app import create_app


def test_health_endpoint():
    app = create_app("testing")
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_index_page_loads():
    app = create_app("testing")
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"ResumeIQ" in response.data
