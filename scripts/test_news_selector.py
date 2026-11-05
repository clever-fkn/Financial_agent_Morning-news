from __future__ import annotations

from bot.config import Settings
from bot.selector import NewsSelector


CANDIDATES = [
    {
        "id": 101,
        "title": "某饮料品牌发布新的包装设计",
        "summary": "公司调整产品外包装，价格和销售渠道保持不变。",
        "source": "公司公告",
    },
    {
        "id": 102,
        "title": "主要央行宣布调整基准利率",
        "summary": "利率变化可能影响汇率、债券、股票和企业融资成本。",
        "source": "央行公告",
    },
    {
        "id": 103,
        "title": "大型 AI 芯片公司公布季度业绩",
        "summary": "营收和数据中心业务增长，管理层同时更新下一季度指引。",
        "source": "公司财报",
    },
    {
        "id": 104,
        "title": "明星在社交媒体分享办公桌照片",
        "summary": "该内容没有涉及公司经营、政策或金融市场。",
        "source": "社交媒体",
    },
    {
        "id": 105,
        "title": "主要产油地区冲突导致原油供应担忧",
        "summary": "市场担忧能源供应中断，国际原油价格出现明显波动。",
        "source": "国际新闻机构",
    },
]


def main() -> None:
    selected = NewsSelector(Settings.from_env()).select(
        candidates=CANDIDATES,
        limit=3,
    )
    titles_by_id = {item["id"]: item["title"] for item in CANDIDATES}

    print(f"Selected result: {selected.model_dump()}")
    print("Selected titles:")
    for news_id in selected.ids:
        print(f"- {news_id}: {titles_by_id[news_id]}")


if __name__ == "__main__":
    main()
