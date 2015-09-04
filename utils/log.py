import logging


def setup_custom_logger(name, log_file):

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    # Create file handler which logs error messages
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.ERROR)
    # Create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.CRITICAL)
    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # Add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger
