import logging


def init_log(level=logging.DEBUG, filename='benchmark.log'):
    logging.basicConfig(level=level)

    logger = logging.getLogger('ProverBenchmark')
    logger.setLevel(logging.DEBUG)
    hdlr = logging.FileHandler(filename)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)


def get_logger():
    return logging.getLogger('ProverBenchmark')
