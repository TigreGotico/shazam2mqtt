"""Entry point: python -m shazam2mqtt"""

import asyncio
import logging
import signal
import sys

from shazam2mqtt.audio import AudioMonitor
from shazam2mqtt.config import Config
from shazam2mqtt.mqtt_client import MqttClient
from shazam2mqtt.state_machine import ShazamStateMachine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("shazam2mqtt")


async def main():
    cfg = Config.from_env()
    logger.info("Configuration: %s", cfg)

    mqtt = MqttClient(cfg)
    mqtt.connect()

    loop = asyncio.get_running_loop()
    force_listen = asyncio.Event()

    sm = ShazamStateMachine(cfg, mqtt, force_listen=force_listen, loop=loop)
    monitor = AudioMonitor(
        noise_gate_db=cfg.noise_gate_db,
        capture_duration=cfg.listen_duration,
        sample_rate=cfg.sample_rate,
        device=cfg.sound_device,
        noise_level_interval=cfg.noise_level_interval,
        noise_level_delta=cfg.noise_level_delta,
        quiet_hysteresis=cfg.quiet_hysteresis,
    )

    # graceful shutdown
    stop_event = asyncio.Event()

    def _on_signal(signum, frame):
        logger.info("Received signal %d, shutting down …", signum)
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _on_signal, sig, None)

    # run monitor in background
    monitor_task = asyncio.create_task(
        monitor.run(
            on_trigger=sm.on_trigger,
            on_noise_level=mqtt.publish_noise_level,
            on_quiet=sm.on_quiet,
            force_listen=force_listen,
        )
    )

    logger.info("shazam2mqtt running (device=%s)", cfg.device_name)
    await stop_event.wait()

    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass

    mqtt.disconnect()
    logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
