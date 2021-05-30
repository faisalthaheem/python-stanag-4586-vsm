# About
Minimal implementation of a STANAG 4586 Vehicle Specific Module (VSM) which uses a lower level library [python-stanag-4586-EDA-v1](https://github.com/faisalthaheem/python-stanag-4586-EDA-v1) to exchange STANAG messages with a remote CUCS.

This library uses asyncio to create two UDP mulicast sockets, one for sending and other for receiving STANG 4586 messages.

Basic operations such as answering to discover broadcast messages from CUCS, granting control and monitor requests or responding with appropriate levels of interoperability statuses is taken care of by this library.

This is one of the libraries which supports the larger project of [Surveillance Simulator](https://github.com/faisalthaheem/surveillance-simulator).

# Usage example
```python
import asyncio
import logging
from stanag4586vsm.stanag_server import *

FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT)

logger = logging.getLogger("main")
logger.setLevel(logging.DEBUG)

async def main():

    loop = asyncio.get_running_loop()
    server = StanagServer(logging.DEBUG)

    logger.debug("Creating server")
    await server.setup_service(loop)

    logger.info("Listening, press Ctrl+C to terminate")
    await asyncio.sleep(3600*100)

    logger.info("Server exiting")

asyncio.run(main())
```