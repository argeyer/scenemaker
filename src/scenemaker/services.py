"""Wire concrete storage, queue, and AI backends from settings."""

from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from scenemaker.ai.base import VideoGenerator
from scenemaker.config import Settings, get_settings
from scenemaker.db.base import make_engine, make_session_factory
from scenemaker.queue.base import JobQueue
from scenemaker.storage.base import ObjectStorage


@dataclass
class Services:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    storage: ObjectStorage
    queue: JobQueue
    generator: VideoGenerator


def build_storage(settings: Settings) -> ObjectStorage:
    if settings.storage_backend == "s3":
        from scenemaker.storage.s3 import S3Storage

        return S3Storage(
            settings.s3_bucket, region=settings.s3_region, endpoint_url=settings.s3_endpoint_url
        )
    from scenemaker.storage.local import LocalStorage

    return LocalStorage(
        settings.storage_local_dir, base_url=settings.api_base_url, secret=settings.jwt_secret
    )


def build_queue(settings: Settings) -> JobQueue:
    if settings.queue_backend == "redis":
        from scenemaker.queue.redis import RedisQueue

        return RedisQueue(settings.redis_url, settings.queue_name)
    from scenemaker.queue.memory import MemoryQueue

    return MemoryQueue()


def build_generator(settings: Settings) -> VideoGenerator:
    if settings.ai_backend == "huggingface":
        from scenemaker.ai.huggingface import HuggingFaceVideoGenerator

        return HuggingFaceVideoGenerator(
            api_token=settings.hf_api_token,
            face_swap_endpoint=settings.hf_face_swap_endpoint,
            avatar_endpoint=settings.hf_avatar_endpoint,
            timeout_seconds=settings.hf_timeout_seconds,
        )
    from scenemaker.ai.fake import FakeVideoGenerator

    return FakeVideoGenerator()


def build_services(settings: Settings | None = None) -> Services:
    settings = settings or get_settings()
    engine = make_engine(settings.database_url)
    return Services(
        settings=settings,
        engine=engine,
        session_factory=make_session_factory(engine),
        storage=build_storage(settings),
        queue=build_queue(settings),
        generator=build_generator(settings),
    )
