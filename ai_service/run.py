import uvicorn

from app.config import config


def main():
    server_cfg = config.server
    host = server_cfg.get("host", "0.0.0.0")
    port = server_cfg.get("port", 8001)

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()