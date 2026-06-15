import os
from src.core.config import settings

def test_config_loading():
    """测试配置是否能正确加载（即使是默认值）"""
    assert settings.APP_NAME == "Second Brain Agent"
    print("✅ Configuration loading test passed.")

def test_env_file_exists():
    """检查 .env 文件是否存在（提醒用户）"""
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        print(f"✅ .env file found at {env_path}")
    else:
        print(f"⚠️ .env file not found. Please copy .env.example to .env and fill in your keys.")

if __name__ == "__main__":
    test_config_loading()
    test_env_file_exists()
