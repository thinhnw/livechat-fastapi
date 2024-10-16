from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_username: str
    mongo_password: str
    mongo_maindb: str
    mongo_testdb: str
    mongo_host: str
    mongo_port: int = 27017
    jwt_secret: str
    jwt_algorithm: str = "HS256" 
    jwt_token_ttl: int = 60 * 60

    @property
    def mongo_uri(self):
        return (
            f"mongodb://{self.mongo_username}:{self.mongo_password}"
            f"@{self.mongo_host}:{self.mongo_port}"
        )

    class Config:
        env_file = ".env"


settings = Settings()