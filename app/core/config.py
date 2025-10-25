from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env 文件路径
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # VLM (截图解析) 配置
    VLM_API_KEY: str
    VLM_API_BASE: str
    VLM_MODEL_NAME: str

    # LLM (对话辅助) 配置
    LLM_API_KEY: str
    LLM_API_BASE: str
    LLM_MODEL_NAME: str

    # 数据存储路径
    DATA_PATH: str = "./data/profiles"


# 创建一个全局可用的配置实例
settings = Settings()