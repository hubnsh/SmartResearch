import pytest
import asyncio
from src.services.web_service import WebService
from src.services.obsidian_service import ObsidianService
import os

@pytest.mark.asyncio
async def test_web_service():
    service = WebService()
    # 测试一个已知的稳定网址
    result = await service.scrape_url("https://www.baidu.com")
    assert result is not None
    assert "url" in result
    assert "title" in result
    print(f"✅ WebService test passed: {result['title']}")

def test_obsidian_service_list():
    # 创建一个临时目录模拟 vault
    vault_path = "./tests/temp_vault"
    os.makedirs(vault_path, exist_ok=True)
    with open(os.path.join(vault_path, "test_note.md"), "w") as f:
        f.write("# Test Note")
    
    service = ObsidianService(vault_path)
    notes = service.get_all_notes()
    assert len(notes) >= 1
    assert any("test_note.md" in n for n in notes)
    
    # 清理
    os.remove(os.path.join(vault_path, "test_note.md"))
    os.rmdir(vault_path)
    print("✅ ObsidianService list test passed.")

if __name__ == "__main__":
    # 手动运行测试
    asyncio.run(test_web_service())
    test_obsidian_service_list()
