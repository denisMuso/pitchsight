import argparse

from dotenv import load_dotenv

from backend.db import database
from pitchsight.data.sync import seed_demo, sync_matches


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="PitchSight native local tools")
    parser.add_argument("command", choices=["init-db", "seed-demo", "sync-matches"])
    args = parser.parse_args()
    engine, factory = database()
    try:
        if args.command == "seed-demo":
            seed_demo(factory)
        elif args.command == "sync-matches":
            sync_matches(factory)
        print(f"{args.command}: completed")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
