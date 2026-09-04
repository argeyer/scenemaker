"""Command-line entry point: `scenemaker api|worker|seed`."""

import argparse
import logging
import sys

from scenemaker import __version__


def _cmd_api(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run(
        "scenemaker.api.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


def _cmd_worker(_args: argparse.Namespace) -> int:
    from scenemaker.worker.main import run_worker

    run_worker()
    return 0


def _cmd_seed(_args: argparse.Namespace) -> int:
    from scenemaker.seed import seed_dev_data
    from scenemaker.services import build_services

    seed_dev_data(build_services())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scenemaker", description="scenemaker backend.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    api = sub.add_parser("api", help="run the HTTP API")
    api.add_argument("--host", default="0.0.0.0")
    api.add_argument("--port", type=int, default=8000)
    api.add_argument("--reload", action="store_true")
    api.set_defaults(func=_cmd_api)

    worker = sub.add_parser("worker", help="run the render job worker")
    worker.set_defaults(func=_cmd_worker)

    seed = sub.add_parser("seed", help="create a demo tenant and template for local development")
    seed.set_defaults(func=_cmd_seed)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
