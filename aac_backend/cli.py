import argparse
import asyncio

from aac_backend.repositories.unit_of_work import unit_of_work
from aac_backend.schemas.auth import UserCreate
from aac_backend.services.user_service import create_user


async def _create_admin(args: argparse.Namespace) -> None:
    async with unit_of_work() as session:
        user = await create_user(
            session,
            UserCreate(
                username=args.username,
                display_name=args.display_name,
                email=args.email,
                password=args.password,
                roles=["admin"],
            ),
            actor_user_id=None,
        )
        print(f"created admin user {user.username} ({user.user_id})")


def main() -> None:
    parser = argparse.ArgumentParser(prog="aac")
    subcommands = parser.add_subparsers(dest="command", required=True)
    admin = subcommands.add_parser("create-admin")
    admin.add_argument("--username", required=True)
    admin.add_argument("--display-name", required=True)
    admin.add_argument("--email", required=True)
    admin.add_argument("--password", required=True)
    args = parser.parse_args()
    if args.command == "create-admin":
        asyncio.run(_create_admin(args))


if __name__ == "__main__":
    main()
