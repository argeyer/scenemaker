def test_list_and_download_template(client, auth):
    listing = client.get("/templates", headers=auth)
    assert listing.status_code == 200
    templates = listing.json()
    assert len(templates) == 1
    assert templates[0]["actor_slots"] == ["lead", "partner"]

    detail = client.get(f"/templates/{templates[0]['id']}", headers=auth)
    assert detail.status_code == 200
    video_url = detail.json()["video_url"]
    assert video_url.startswith("http://testserver/files/")

    # The signed URL works without an Authorization header, like a presigned S3 URL.
    video = client.get(video_url)
    assert video.status_code == 200
    assert video.content == b"PLACEHOLDER-TEMPLATE-VIDEO"


def test_tampered_download_link_rejected(client, auth):
    templates = client.get("/templates", headers=auth).json()
    video_url = client.get(f"/templates/{templates[0]['id']}", headers=auth).json()["video_url"]
    assert client.get(video_url.replace("token=", "token=0")).status_code == 403
    assert client.get(video_url.replace("scene.mp4", "other.mp4")).status_code == 403


def test_unknown_template_404(client, auth):
    assert client.get("/templates/does-not-exist", headers=auth).status_code == 404
