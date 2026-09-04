import pytest

from scenemaker.db.models import JobStatus, RenderJob
from scenemaker.worker.tasks import process_job


def upload_selfie(client, auth, name="me.jpg", data=b"\xff\xd8selfie"):
    response = client.post("/selfies", headers=auth, files={"file": (name, data, "image/jpeg")})
    assert response.status_code == 201, response.text
    return response.json()


def run_queue(services):
    while (job_id := services.queue.pop(0.01)) is not None:
        process_job(services, job_id)


def test_selfie_upload_validation(client, auth):
    assert (
        client.post(
            "/selfies", headers=auth, files={"file": ("x.txt", b"hi", "text/plain")}
        ).status_code
        == 415
    )
    assert (
        client.post(
            "/selfies", headers=auth, files={"file": ("x.jpg", b"", "image/jpeg")}
        ).status_code
        == 400
    )
    upload_selfie(client, auth)
    assert len(client.get("/selfies", headers=auth).json()) == 1


def test_face_swap_flow_with_multiple_selfies(client, auth, services, give_credits):
    give_credits("ada@example.com", 1)
    template = client.get("/templates", headers=auth).json()[0]
    lead = upload_selfie(client, auth, "lead.jpg", b"\xff\xd8lead")
    partner = upload_selfie(client, auth, "partner.jpg", b"\xff\xd8partner")

    created = client.post(
        "/jobs",
        headers=auth,
        json={
            "template_id": template["id"],
            "kind": "face_swap",
            "selfies": [
                {"selfie_id": lead["id"], "slot": "lead"},
                {"selfie_id": partner["id"], "slot": "partner"},
            ],
        },
    )
    assert created.status_code == 202, created.text
    job = created.json()
    assert job["status"] == "queued"
    assert job["output_url"] is None
    assert client.get("/auth/me", headers=auth).json()["credits"] == 0

    run_queue(services)

    done = client.get(f"/jobs/{job['id']}", headers=auth).json()
    assert done["status"] == "done"
    assert done["attempts"] == 1
    assert done["output_url"]

    video = client.get(done["output_url"])
    assert video.status_code == 200
    assert video.content.startswith(b"FAKE-VIDEO kind=face_swap")
    assert b"slots=lead,partner" in video.content

    kind, request = services.generator.calls[0]
    assert kind == "face_swap"
    assert request.selfies == {"lead": b"\xff\xd8lead", "partner": b"\xff\xd8partner"}
    assert request.template_video == b"PLACEHOLDER-TEMPLATE-VIDEO"


def test_avatar_flow_uses_motion_preset(client, auth, services, give_credits):
    give_credits("ada@example.com", 1)
    template = client.get("/templates", headers=auth).json()[0]
    selfie = upload_selfie(client, auth)

    created = client.post(
        "/jobs",
        headers=auth,
        json={
            "template_id": template["id"],
            "kind": "avatar",
            "selfies": [{"selfie_id": selfie["id"], "slot": "avatar"}],
            "motion_preset": "turn_and_smile",
        },
    )
    assert created.status_code == 202, created.text
    run_queue(services)

    kind, request = services.generator.calls[0]
    assert kind == "avatar"
    assert request.params == {"motion_preset": "turn_and_smile"}
    assert client.get(f"/jobs/{created.json()['id']}", headers=auth).json()["status"] == "done"


@pytest.mark.parametrize(
    "kind, selfies, preset, message",
    [
        ("face_swap", [("villain", None)], None, "no actor slots"),
        ("face_swap", [("lead", None), ("lead", None)], None, "once"),
        ("avatar", [("lead", None)], None, "exactly one selfie"),
        ("avatar", [("avatar", None)], "moonwalk", "motion preset"),
        ("face_swap", [("lead", "missing-id")], None, "unknown selfie"),
    ],
)
def test_job_validation(client, auth, give_credits, kind, selfies, preset, message):
    give_credits("ada@example.com", 5)
    template = client.get("/templates", headers=auth).json()[0]
    selfie = upload_selfie(client, auth)
    body = {
        "template_id": template["id"],
        "kind": kind,
        "selfies": [{"selfie_id": sid or selfie["id"], "slot": slot} for slot, sid in selfies],
    }
    if preset:
        body["motion_preset"] = preset
    response = client.post("/jobs", headers=auth, json=body)
    assert response.status_code == 400, response.text
    assert message in response.json()["detail"]
    assert client.get("/auth/me", headers=auth).json()["credits"] == 5


def test_job_requires_credit(client, auth):
    template = client.get("/templates", headers=auth).json()[0]
    selfie = upload_selfie(client, auth)
    response = client.post(
        "/jobs",
        headers=auth,
        json={
            "template_id": template["id"],
            "kind": "face_swap",
            "selfies": [{"selfie_id": selfie["id"], "slot": "lead"}],
        },
    )
    assert response.status_code == 402


def test_failed_render_retries_then_fails(client, auth, services, give_credits):
    services.generator.fail = True
    give_credits("ada@example.com", 1)
    template = client.get("/templates", headers=auth).json()[0]
    selfie = upload_selfie(client, auth)
    job_id = client.post(
        "/jobs",
        headers=auth,
        json={
            "template_id": template["id"],
            "kind": "face_swap",
            "selfies": [{"selfie_id": selfie["id"], "slot": "lead"}],
        },
    ).json()["id"]

    run_queue(services)

    job = client.get(f"/jobs/{job_id}", headers=auth).json()
    assert job["status"] == "failed"
    assert job["attempts"] == services.settings.job_max_attempts == 2
    assert "configured to fail" in job["error"]
    assert job["output_url"] is None


def test_users_cannot_see_each_others_data(client, register, services, give_credits):
    ada = register("ada@example.com")
    bob = register("bob@example.com")
    give_credits("ada@example.com", 1)
    template = client.get("/templates", headers=ada).json()[0]
    selfie = upload_selfie(client, ada)

    job_id = client.post(
        "/jobs",
        headers=ada,
        json={
            "template_id": template["id"],
            "kind": "face_swap",
            "selfies": [{"selfie_id": selfie["id"], "slot": "lead"}],
        },
    ).json()["id"]

    assert client.get("/selfies", headers=bob).json() == []
    assert client.get("/jobs", headers=bob).json() == []
    assert client.get(f"/jobs/{job_id}", headers=bob).status_code == 404

    # Bob cannot attach Ada's selfie to his own job.
    give_credits("bob@example.com", 1)
    stolen = client.post(
        "/jobs",
        headers=bob,
        json={
            "template_id": template["id"],
            "kind": "face_swap",
            "selfies": [{"selfie_id": selfie["id"], "slot": "lead"}],
        },
    )
    assert stolen.status_code == 400
    with services.session_factory() as db:
        assert db.query(RenderJob).filter_by(status=JobStatus.QUEUED).count() == 1
