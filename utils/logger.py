# ---- Logging setup ----
import logging 

def init_logger(name:str) -> logging.Logger:
    logging.basicConfig(
        level=logging.ERROR,                # or DEBUG for more detail
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[logging.StreamHandler()]  # outputs to console
    )
    logger = logging.getLogger(name)
    return logger