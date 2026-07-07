"""WS2812B LED strip driver for Spotifoni."""

_strip = None

SPI_PIN = 10
DEFAULT_COUNT = 8
DEFAULT_BRIGHTNESS = 50


def init(num_leds=DEFAULT_COUNT, brightness=DEFAULT_BRIGHTNESS):
    global _strip
    try:
        from rpi_ws281x import PixelStrip, ws
        _strip = PixelStrip(num_leds, SPI_PIN,
                            strip_type=ws.WS2812_STRIP,
                            brightness=brightness)
        _strip.begin()
        return True
    except (ImportError, RuntimeError) as e:
        print(f"WS2812 init skipped: {e}")
        _strip = None
        return False


def set_pixel(n, r, g, b):
    if _strip and 0 <= n < _strip.numPixels():
        _strip.setPixelColorRGB(n, r, g, b)


def set_all(r, g, b):
    if _strip:
        for i in range(_strip.numPixels()):
            _strip.setPixelColorRGB(i, r, g, b)


def clear():
    set_all(0, 0, 0)
    show()


def show():
    if _strip:
        _strip.show()
