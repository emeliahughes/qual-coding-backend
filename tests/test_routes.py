from app import app

def test_next_video():
    with app.test_client() as client:
        res = client.get("/api/next-video")
        assert res.status_code == 200
        assert "videoUrl" in res.get_json()
