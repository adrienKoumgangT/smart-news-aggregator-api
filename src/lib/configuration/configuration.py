import os
from dataclasses import dataclass, field
from typing import TypeVar, Optional, Type, List

from dotenv import load_dotenv

from src.lib.log.api_logger import ApiLogger


def to_env_var_name(key: str) -> str:
    return key.strip().replace(".", "_").replace("-", "_").upper()

T = TypeVar("T")

def get_env_var(name: str, default: Optional[T] = None, var_type: Type[T] = str, delimiter: str = ","):
    var_name = to_env_var_name(name)
    value = os.getenv(var_name, default)

    # print(f"{var_name} = {value}")

    if value is None:
        return default

    try:
        if var_type == bool:
            return str(value).strip().lower() in ("true", "1", "yes", "on")
        elif var_type == int:
            return int(value)
        elif var_type == float:
            return float(value)
        elif var_type == list:
            return [item.strip() for item in value.split(delimiter)]
        elif var_type == str:
            return str(value)
        else:
            raise ValueError(f"Unsupported var_type: {var_type}")
    except Exception as e:
        raise ValueError(f"Failed to parse env var '{name}' ('{var_name}') as {var_type.__name__}: {e}")


@dataclass
class MongoConfig:
    host: str = field(default_factory=lambda: get_env_var("mongodb.host", "localhost"))
    port: int = field(default_factory=lambda: get_env_var("mongodb.port", 27017, int))
    username: str = field(default_factory=lambda: get_env_var("mongodb.username", ""))
    password: str = field(default_factory=lambda: get_env_var("mongodb.password", ""))

    uri: str = field(default_factory=lambda: get_env_var("mongodb.uri", "mongodb://localhost:27017/"))

    database: str = field(default_factory=lambda: get_env_var("mongodb.database", "smart-news-aggregator"))

@dataclass
class RedisConfig:
    host: str = field(default_factory=lambda: get_env_var("redis.host", "localhost"))
    port: int = field(default_factory=lambda: get_env_var("redis.port", 6379, int))
    db: int = field(default_factory=lambda: get_env_var("redis.db", 0, int))

    uri: str = field(default_factory=lambda: get_env_var("redis.uri", "redis://localhost:6379"))

@dataclass
class ExternAPIConfig:
    enable: bool = field(default_factory=lambda: get_env_var("enable", False, bool))
    access_key: str = field(default_factory=lambda: get_env_var("access_key", ""))
    max_request: int = field(default_factory=lambda: get_env_var("max_request", 0, int))

@dataclass
class Config:
    prod: bool = field(default_factory=lambda: get_env_var("prod", False, bool))
    debug: bool = field(default_factory=lambda: get_env_var("debug", False, bool))
    log: bool = field(default_factory=lambda: get_env_var("log", True, bool))
    port: int = field(default_factory=lambda: get_env_var("port", 5000, int))

    allowed_hosts: List[str] = field(default_factory=lambda: get_env_var("allowed.hosts", "localhost,127.0.0.1", list))
    swagger_allowed: bool = field(default_factory=lambda: get_env_var("swagger.allowed", False, bool))
    swagger_allowed_hosts: List[str] = field(default_factory=lambda: get_env_var("swagger.allowed.hosts", "127.0.0.1/32", list))

    mongo: MongoConfig = field(default_factory=MongoConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)



class ConfigManager:
    def __init__(self):
        self._config = None
        self.reload()

    def reload(self):
        # Reload .env
        env_file = os.getenv("FLASK_ENV_FILE", ".env.dev")
        # print(f"env_file: {env_file}")
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '..', env_file)
        # print(f"env_path: {env_path}")
        api_logger = ApiLogger(f"[CONFIGURATION] [RELOAD] [ENV] : path file={env_path}")
        load_dotenv(dotenv_path=env_path, verbose=True, override=True)
        api_logger.print_log()

        # Rebuild the config dataclass
        self._config = Config()

    def get(self) -> Config:
        return self._config


config_manager = ConfigManager()
config = config_manager.get()


