"""radiochannel.py: Mote radio channel changing functions."""

import time

from moteconnection.packet import PacketDispatcher, Packet
import struct

import logging

log = logging.getLogger(__name__)

__author__ = "Raido Pahtma"
__license__ = "MIT"


class RadioChannelChanger(object):
    DP_HEARTBEAT = 0x00
    DP_PARAMETER = 0x10
    DP_ERROR_ID = 0xF0
    DP_ERROR_SEQ = 0xF1
    DP_SET_PARAMETER_WITH_ID = 0x31
    PARAMETER_NAME = "radio_channel"

    def __init__(self, connection):
        self._connection = connection
        self._radio_channel = None
        self._set_channel = None
        self._dispatcher = PacketDispatcher(0x80)
        self._dispatcher.register_receiver(self._receive)
        self._connection.register_dispatcher(self._dispatcher)
        self._watchers = set()
        self._last_boot = time.time()

    def get(self):
        return self._radio_channel

    def set(self, channel):
        if channel is not None:
            assert isinstance(channel, (int, long))
            self._set_channel = channel
            if self._set_channel != self._radio_channel:
                self._send_set_channel()
        else:
            self._set_channel = None
            log.debug("channel set to None")

    def _send_set_channel(self):
        if self._set_channel is not None:
            p = Packet(0x80)
            p.payload = chr(self.DP_SET_PARAMETER_WITH_ID) \
                        + chr(len(self.PARAMETER_NAME)) \
                        + chr(1) \
                        + self.PARAMETER_NAME \
                        + chr(self._set_channel)
            self._dispatcher.send(p)

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
                    log.warning("Node restarted %ds ago", uptime)
                    self._radio_channel = 0

                self._last_boot = time.time() - uptime

                self.check_channel()

            elif header == self.DP_PARAMETER:
                fmt = "!BBBBB"
                fmt_len = struct.calcsize(fmt)
                if len(packet.payload) > fmt_len:
                    _, _, _, id_len, v_len = struct.unpack(fmt, packet.payload[:fmt_len])
                    pid = packet.payload[fmt_len:fmt_len + id_len]
                    if pid == self.PARAMETER_NAME and v_len == 1:
                        ch = ord(packet.payload[-1])
                        if ch != self._radio_channel:
                            self._radio_channel = ch
                            for watcher in self._watchers:
                                watcher(ch)

                        log.info("Radio channel is %d", self._radio_channel)
                        self.check_channel()
                    else:
                        log.debug("Unexpected parameter %s: %s", pid, packet.payload[fmt_len + id_len:])
                else:
                    log.warning("Packet too short %d", len(packet.payload))

            elif header == self.DP_ERROR_ID:
                log.warning("Parameter ID error %s", packet.payload.encode("hex"))
                # most likely the error was EBUSY, maybe EOFF - todo proper packets with serdepa and error handling
                if self._set_channel != self._radio_channel:
                    self._send_set_channel()
            elif header == self.DP_ERROR_SEQ:
                log.warning("Parameter seq error %s", packet.payload.encode("hex"))
            else:
                log.debug("Unexpected header %02X for packet %s", header, packet.payload.encode("hex"))

    def register_watcher(self, watcher):
        assert callable(watcher)
        self._watchers.add(watcher)

    def deregister_watcher(self, watcher):
        if watcher in self._watchers:
            self._watchers.remove(watcher)
