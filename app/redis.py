import aioredis
from app.config import settings


async def get_redis():
    redis = await aioredis.from_url(
        f"redis://{settings.redis_host}:{settings.redis_port}",
        password=settings.redis_password,
        decode_responses=True,
    )
    try:
        yield redis
    finally:
        await redis.close()
