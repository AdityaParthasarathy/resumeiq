from app import create_app


def _client():
    app = create_app("testing")
    return app.test_client()


def test_nonexistent_resume_returns_styled_404():
    client = _client()

    response = client.get("/resume/9999")

    assert response.status_code == 404
    assert b"Page not found" in response.data
    assert b"Upload a resume" in response.data


def test_nonexistent_route_returns_styled_404():
    client = _client()

    response = client.get("/this-route-does-not-exist")

    assert response.status_code == 404
    assert b"Page not found" in response.data
