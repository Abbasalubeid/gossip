import random
import time

from util import CHARACTERISTIC_UUID, UUID, APPEARANCE, ADVERTISEMENT_TIME, DOWN_TIME, PERIPHERAL_TIME
from bluez_peripheral.util import *
from bluez_peripheral.advert import Advertisement
from bluez_peripheral.gatt.service import Service
from bluez_peripheral.gatt.characteristic import characteristic, CharacteristicFlags as CharFlags
import os
from aes_crypto import encrypt
import struct
import asyncio


class MessageService(Service):
    """ Service for sending messages """

    def __init__(self):
        super().__init__(UUID, True)

    @characteristic(CHARACTERISTIC_UUID, CharFlags.NOTIFY)
    def post(self, options):
        """ This function is called when the characteristic is read. """
        pass

    def send_message(self, new_message):
        """ Send the specified message. """
        new_message = new_message if type(new_message) is bytes else new_message.encode()
        encrypted_msg = encrypt(new_message)
        length = len(encrypted_msg)
        message = struct.pack("<" + str(length) + "s", encrypted_msg)
        self.post.changed(message)


class Peripheral:
    """ Handles BLE communication as a peripheral. """

    def __init__(self, quit_event, new_posts_event, hub_name):
        self.posts = None
        self.quit_event = quit_event
        self.new_posts_event = new_posts_event
        self.hub_name = hub_name
        self.service = MessageService()

    def set_posts(self, posts):
        """ Set the posts being sent out over BLE. """
        self.posts = posts

    def advertise(self):
        """ Start advertising the posts. """
        # asyncio.set_event_loop(asyncio.new_event_loop())
        # loop = asyncio.get_event_loop()
        # coroutine = self.__run()
        # loop.run_until_complete(coroutine)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.__run())

    async def __run(self):
        bus = await get_message_bus()
        await self.service.register(bus)

        adapter = await Adapter.get_first(bus)

        # Start an advert.
        advert = Advertisement(self.hub_name, [UUID], APPEARANCE, ADVERTISEMENT_TIME)
        await advert.register(bus, adapter)
        start = time.time()
        while time.time() - start < PERIPHERAL_TIME and not self.quit_event.is_set():
            index = 0 if not self.posts else random.randrange(0, len(self.posts))    # start broadcast at random post
            while time.time() - start < PERIPHERAL_TIME and not self.quit_event.is_set():
                if not self.posts:
                    continue
                self.service.send_message(self.posts[index])     # broadcast post
                index = (index + 1) if (index < len(self.posts)-1) else 0  # increment index within range
                await asyncio.sleep(DOWN_TIME)
                if self.new_posts_event.is_set():
                    self.new_posts_event.clear()     # clear new post event when handled
                    break                            # break out of post loop if new posts