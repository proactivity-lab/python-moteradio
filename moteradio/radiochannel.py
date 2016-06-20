"""radiochannel.py: Mote radio channel changing functions."""

import time

from moteconnection.packet import PacketDispatcher, Packet
import struct

import logging
log = logging.getLogger(__name__)

__author__ = "Raido Pahtma"
__license__ = "MIT"

version = "0.1.0.dev1"


class RadioChannelChanger(object):
    DP_HEARTBEAT = 0x00
    DP_PARAMETER = 0x10
    DP_SET_PARAMETER_WITH_ID = 0x31
    PARAMETER_NAME = "radio_channel"

    def __init__(self, connection):
        self._connection = connection
        self._radio_channel = 0
        self._set_channel = None
        self._dispatcher = PacketDispatcher(0x80)
        self._dispatcher.register_receiver(self._receive)
        self._connection.register_dispatcher(self._dispatcher)
        self._last_boot = time.time()

    def get(self):
        return self._radio_channel

    def set(self, channel):
        self._set_channel = channel
        if channel is not None:
            p = Packet(0x80)
            p.payload = chr(self.DP_SET_PARAMETER_WITH_ID) \
                        + chr(len(self.PARAMETER_NAME)) \
                        + chr(1) \
                        + self.PARAMETER_NAME \
                        + chr(channel)
            self._dispatcher.send(p)
        else:
            log.debug("channel set to None")

    def check_channel(self):
        if self._set_channel is not None:
            if self._radio_channel != self._set_channel:
                self.set(self._set_channel)

    def _receive(self, packet):
        if len(packet.payload) > 0:
            header = ord(packet.payload[0])
            if header == self.DP_HEARTBEAT:
                _, _, uptime = struct.unpack("!BQL", packet.payload)
                if time.time() - self._last_boot > uptime + 3:  # allow 3 second error
                    log.warning("Node restarted {:d}s ago".format(uptime))
                    self._radio_channel = 0

                self._last_boot = time.time() - uptime

                self.check_channel()

            elif header == self.DP_PARAMETER:
                fmt = "!BBBBB"
                fmt_len = struct.calcsize(fmt)
                if len(packet.payload) > fmt_len:
                    _, _, _, id_len, v_len = struct.unpack(fmt, packet.payload[:fmt_len])
                    id = packet.payload[fmt_len:fmt_len+id_len]
                    if id == self.PARAMETER_NAME and v_len == 1:
                        self._radio_channel = ord(packet.payload[-1])
                        log.info("Radio channel is {:d}".format(self._radio_channel))
                        self.check_channel()
                    else:
                        log.debug("Unexpected parameter {:s}: {:s}".format(id, packet.payload[fmt_len+id_len:]))
                else:
                    log.warning("Packet too short {:d}".format(len(packet.payload)))

            else:
                log.debug("Unexpected header {:04X} for packet {}".format(header, packet.payload.encode("hex")))
