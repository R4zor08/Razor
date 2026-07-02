"""System tray icon for background Razor operation."""

from __future__ import annotations

from collections.abc import Callable

from utils.logger import get_logger

logger = get_logger(__name__)


def _build_icon_image():
    from PIL import Image, ImageDraw

    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, size - 4, size - 4), fill=(30, 144, 255, 255))
    draw.text((18, 20), "R", fill=(255, 255, 255, 255))
    return image


class TrayIcon:
    """Minimal pystray wrapper for Razor background mode."""

    def __init__(
        self,
        *,
        on_activate: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
        tooltip: str = "Razor AI",
    ) -> None:
        self.on_activate = on_activate
        self.on_quit = on_quit
        self.tooltip = tooltip
        self._icon = None

    def run(self) -> None:
        try:
            import pystray
        except ImportError:
            logger.warning("pystray not installed; running without system tray.")
            self._run_headless()
            return

        menu_items = []
        if self.on_activate:
            menu_items.append(pystray.MenuItem("Activate (listen)", lambda: self._call(self.on_activate)))
        menu_items.append(pystray.MenuItem("Quit", lambda: self._quit()))

        self._icon = pystray.Icon(
            "razor",
            _build_icon_image(),
            self.tooltip,
            menu=pystray.Menu(*menu_items),
        )
        logger.info("System tray icon started.")
        self._icon.run()

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.visible = False
                self._icon.stop()
            except Exception as exc:
                logger.debug("Tray stop: %s", exc)
            self._icon = None

    def _run_headless(self) -> None:
        import time

        logger.info("Headless background mode (install pystray for tray icon).")
        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            pass
        finally:
            if self.on_quit:
                self.on_quit()

    def _quit(self) -> None:
        """Quit from tray menu — shutdown then stop icon so run() returns cleanly."""
        try:
            if self.on_quit:
                self.on_quit()
        except Exception as exc:
            logger.warning("Quit handler failed: %s", exc)
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception as exc: 
                logger.debug("Tray stop on quit: %s", exc)

    @staticmethod
    def _call(callback: Callable[[], None] | None) -> None:
        if callback:
            try:
                callback()
            except Exception as exc:
                logger.warning("Tray callback failed: %s", exc)
