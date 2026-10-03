"""Виды имущества, которые можно принять через консоль.

Новый вид транспорта или вещи: создать подкласс в domain и добавить его сюда.
Консоль сама поймёт, какие поля спросить: Transport → «простота», EnergyConsumer → кВт·ч.
"""

from vyshkat.domain import (
    Asset,
    Bicycle,
    ChargingCabinet,
    DockStation,
    ElectricBike,
    ElectricScooter,
    Helmet,
)

ASSET_KINDS: tuple[type[Asset], ...] = (
    ElectricScooter,
    ElectricBike,
    Bicycle,
    Helmet,
    DockStation,
    ChargingCabinet,
)
