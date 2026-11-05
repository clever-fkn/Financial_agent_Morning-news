from __future__ import annotations

from pydantic import ValidationError

from bot.models import SelectedNews


def main() -> None:
    valid = SelectedNews.model_validate({"ids": [5, 2, 9]})
    print(f"Valid result: {valid.model_dump()}")

    invalid_examples = [
        {"ids": [5, 5]},
        {"ids": [0, 2]},
        {"ids": []},
    ]
    for example in invalid_examples:
        try:
            SelectedNews.model_validate(example)
        except ValidationError as exc:
            first_error = exc.errors()[0]["msg"]
            print(f"Rejected {example}: {first_error}")


if __name__ == "__main__":
    main()
