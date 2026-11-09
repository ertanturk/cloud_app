import logging

from .config import get_config


class ProjectLogger:
    _instance: logging.Logger | None = None
    _LOGGER_NAME = "CloudBackend"
    _LOG_FILE = get_config().LOG_FILE_PATH

    @classmethod
    def initialize(
        cls, log_file: str = _LOG_FILE, level: int = logging.INFO
    ) -> logging.Logger:
        """Initializes the shared logger instance once with your custom structure."""
        if cls._instance is not None:
            return cls._instance

        # Create the core root-level logger for the project
        logger = logging.getLogger(cls._LOGGER_NAME)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # Prevent logs from leaking to the default root logger

        log_format = logging.Formatter(
            fmt="[%(asctime)s] / [%(levelname)s] / [%(name)s] / [%(filename)s:%(lineno)d] / %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)

        # File Handler
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(level)
            file_handler.setFormatter(log_format)
            logger.addHandler(file_handler)
        except OSError as exc:
            console_handler.handle(
                logger.makeRecord(
                    cls._LOGGER_NAME,
                    logging.ERROR,
                    __file__,
                    0,
                    "Failed to initialize file logging: %s",
                    (exc,),
                    None,
                )
            )

        cls._instance = logger
        return cls._instance

    @classmethod
    def get_logger(cls, module_name: str | None = None) -> logging.Logger:
        """
        Retrieves the logger instance.
        Pass a module name (e.g., __name__) to easily track which file sent the log.
        """
        if cls._instance is None:
            cls.initialize()

        if module_name:
            return logging.getLogger(f"{cls._LOGGER_NAME}.{module_name}")

        return logging.getLogger(cls._LOGGER_NAME)
