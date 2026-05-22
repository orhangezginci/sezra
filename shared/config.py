import os


class Settings:
    project_name: str = os.getenv("PROJECT_NAME", "sezra")

    rabbitmq_host: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
    rabbitmq_port: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    rabbitmq_user: str = os.getenv("RABBITMQ_USER", "sezra")
    rabbitmq_password: str = os.getenv("RABBITMQ_PASSWORD", "sezra")

    postgres_host: str = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_user: str = os.getenv("POSTGRES_USER", "sezra")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "sezra")
    postgres_db: str = os.getenv("POSTGRES_DB", "sezra")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:"
            f"{self.postgres_password}@{self.postgres_host}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()