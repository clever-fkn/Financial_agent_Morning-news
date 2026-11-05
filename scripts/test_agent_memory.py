from __future__ import annotations

from uuid import uuid4

from bot.agent import NewsAgent
from bot.config import Settings


def main() -> None:
    settings = Settings.from_env()
    thread_id = f"memory-demo-{uuid4()}"

    first_agent = NewsAgent(settings)
    first_answer = first_agent.answer(
        "请记住：我的测试代号是青竹。只需要确认你记住了。",
        thread_id=thread_id,
    )
    first_agent.close()

    second_agent = NewsAgent(settings)
    remembered_answer = second_agent.answer(
        "我的测试代号是什么？",
        thread_id=thread_id,
    )
    isolated_answer = second_agent.answer(
        "我的测试代号是什么？",
        thread_id=f"{thread_id}-other",
    )
    second_agent.close()

    print(f"Thread id: {thread_id}")
    print(f"First answer: {first_answer}")
    print(f"Same thread answer: {remembered_answer}")
    print(f"Other thread answer: {isolated_answer}")


if __name__ == "__main__":
    main()
