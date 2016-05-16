"""Implementation of KNXnet/IP communication with KNXnet/IP gateways."""
import asyncio
import logging

import libknx

__all__ = ['KnxGatewaySearch',
           'KnxGatewayDescription']

LOGGER = logging.getLogger(__name__)

class KnxGatewaySearch(asyncio.DatagramProtocol):

    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.transport = None
        self.responses = set()

    def connection_made(self, transport):
        self.transport = transport
        self.peername = self.transport.get_extra_info('peername')
        self.sockname = self.transport.get_extra_info('sockname')
        packet = libknx.messages.KnxSearchRequest(sockname=self.sockname)
        self.transport.get_extra_info('socket').sendto(packet.get_message(), ('224.0.23.12', 3671))

    def datagram_received(self, data, addr):
        try:
            LOGGER.debug('Parsing KnxSearchResponse')
            response = libknx.messages.KnxSearchResponse(data)

            if response:
                self.responses.add((addr, response))
            else:
                LOGGER.info('Not a valid search response!')
        except Exception as e:
            LOGGER.exception(e)


class KnxGatewayDescription(asyncio.DatagramProtocol):

    def __init__(self, future, loop=None, timeout=2):
        self.future = future
        self.loop = loop or asyncio.get_event_loop()
        self.transport = None
        self.response = None
        self.timeout = timeout

    def connection_made(self, transport):
        self.transport = transport
        self.peername = self.transport.get_extra_info('peername')
        self.sockname = self.transport.get_extra_info('sockname')
        self.wait = self.loop.call_later(self.timeout, self.connection_timeout)

        packet = libknx.messages.KnxDescriptionRequest(sockname=self.sockname)
        self.transport.sendto(packet.get_message())

    def connection_timeout(self):
        LOGGER.debug('Description timeout')
        self.transport.close()
        self.future.set_result(False)

    def datagram_received(self, data, addr):
        self.wait.cancel()
        self.transport.close()
        try:
            LOGGER.debug('Parsing KnxDescriptionResponse')
            self.response = libknx.KnxDescriptionResponse(data)

            if self.response:
                self.future.set_result(self.response)
            else:
                LOGGER.info('Not a valid description response!')
                self.future.set_result(False)
        except Exception as e:
            LOGGER.exception(e)