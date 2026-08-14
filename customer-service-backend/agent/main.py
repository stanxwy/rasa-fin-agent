import uvicorn

from agent.conf.settings import settings
from agent.utils.logging_config import setup_logging

if __name__ == '__main__':
    logger = setup_logging("INFO")
    
    uvicorn.run(
        app="agent.api.app:app", # package.module:object
        host=settings.app_host,
        port=settings.app_port
    )