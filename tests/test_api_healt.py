def test_happy_healt(client):
    response = client.get("v1/")

    assert response.json() == {"status": "ok"}
    assert response.status_code == 200
