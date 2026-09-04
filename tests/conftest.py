import pytest
from fastapi.testclient import TestClient

from scenemaker.ai.fake import FakeVideoGenerator
from scenemaker.api.app import create_app
from scenemaker.config import Settings
from scenemaker.db.base import Base, make_engine, make_session_factory
from scenemaker.queue.memory import MemoryQueue
from scenemaker.seed import DEMO_TENANT_SLUG, seed_dev_data
from scenemaker.services import Services
from scenemaker.storage.local import LocalStorage


@pytest.fixture
def services(tmp_path) -> Services:
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        jwt_secret="test-secret-that-is-at-least-32-bytes-long",
        storage_local_dir=str(tmp_path / "storage"),
        api_base_url="http://testserver",
        job_max_attempts=2,
    )
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)
    svc = Services(
        settings=settings,
        engine=engine,
        session_factory=make_session_factory(engine),
        storage=LocalStorage(
            settings.storage_local_dir, base_url=settings.api_base_url, secret=settings.jwt_secret
        ),
        queue=MemoryQueue(),
        generator=FakeVideoGenerator(),
    )
    seed_dev_data(svc)
    return svc


@pytest.fixture
def client(services: Services) -> TestClient:
    return TestClient(create_app(services))


@pytest.fixture
def register(client: TestClient):
    def _register(email: str = "ada@example.com", tenant: str = DEMO_TENANT_SLUG) -> dict:
        response = client.post(
            "/auth/register",
            json={"tenant_slug": tenant, "email": email, "password": "correct horse"},
        )
        assert response.status_code == 201, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _register


@pytest.fixture
def auth(register) -> dict:
    return register()


@pytest.fixture
def give_credits(services: Services):
    from sqlalchemy import select

    from scenemaker.db.models import User

    def _give(email: str, credits: int) -> None:
        with services.session_factory() as db:
            user = db.scalar(select(User).where(User.email == email))
            user.credits = credits
            db.commit()

    return _give
