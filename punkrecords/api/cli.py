"""`punkrecords-serve` 入口：启动 Uvicorn。"""

import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="PunkRecords HTTP API (Uvicorn)")
    parser.add_argument(
        "--host",
        default=os.environ.get("PUNKRECORDS_HOST", "127.0.0.1"),
        help="监听地址",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PUNKRECORDS_PORT", "8765")),
        help="监听端口",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="开发模式自动重载",
    )
    args = parser.parse_args()
    uvicorn.run(
        "punkrecords.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
