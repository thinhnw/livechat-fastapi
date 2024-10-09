from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_username: str
    mongo_password: str
    mongo_database: str
    mongo_testdb: str
    mongo_host: str
    mongo_port: int = 27017
    jwt_secret: str

    @property
    def mongo_uri(self):
        return (
            f"mongodb://{self.mongo_username}:{self.mongo_password}"
            f"@{self.mongo_host}:{self.mongo_port}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
