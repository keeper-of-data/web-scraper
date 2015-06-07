import logging

def setup_custom_logger(name, log_file):

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    # Create file handler which logs even debug messages
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    # Create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    # Create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # Add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)



    # formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    # handler = logging.StreamHandler()
    # handler.setFormatter(formatter)

    # logger = logging.getLogger(name)
    # logger.setLevel(logging.DEBUG)
    # logger.addHandler(handler)
    return logger
