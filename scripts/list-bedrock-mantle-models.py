"""List the model IDs exposed by the Bedrock Mantle endpoint."""

import argparse

from openai import OpenAI
from openai.providers import bedrock


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="anekur-admin")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument(
        "--contains",
        default=None,
        help="Optional case-insensitive text used to filter model IDs.",
    )
    args = parser.parse_args()

    base_url = f"https://bedrock-mantle.{args.region}.api.aws/v1"
    client = OpenAI(
        provider=bedrock(
            profile=args.profile,
            region=args.region,
            base_url=base_url,
        ),
    )
    model_ids = sorted(model.id for model in client.models.list().data)
    if args.contains:
        needle = args.contains.casefold()
        model_ids = [
            model_id for model_id in model_ids if needle in model_id.casefold()
        ]

    for model_id in model_ids:
        print(model_id)


if __name__ == "__main__":
    main()
