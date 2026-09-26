import uvicorn

from source.config import settings
from source.factory import create_api, create_container
from source.utils import setup_logger


def main() -> None:
    setup_logger()
    uvicorn.run(
        create_api(create_container()),
        host=settings.api.host,
        port=settings.api.port,
        log_config=None,
    )


if __name__ == "__main__":
    main()
