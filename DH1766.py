from qcodes import VisaInstrument
from qcodes.instrument.channel import InstrumentChannel, ChannelList
from qcodes.validators import Numbers

from time import sleep


class DH1766Channel(InstrumentChannel):

    CHANNEL_LIMITS = {
        1: {"voltage": (0, 32), "current": (0, 3)},
        2: {"voltage": (0, 32), "current": (0, 3)},
        3: {"voltage": (0, 6),  "current": (0, 3)},
    }

    def __init__(self, parent: VisaInstrument, name: str, channel: int):

        super().__init__(parent, name)
        self.channel_id = channel

        limits = self.CHANNEL_LIMITS[channel]
        vmin, vmax = limits["voltage"]
        imin, imax = limits["current"]

        self.add_parameter(
            name="voltage",
            unit="V",
            get_cmd=self._get_voltage,
            set_cmd=self._set_voltage,
            vals=Numbers(vmin, vmax),
        )

        self.add_parameter(
            name="current",
            unit="A",
            get_cmd=self._get_current,
            set_cmd=self._set_current,
            vals=Numbers(imin, imax),
        )

        self.add_parameter(
            name="output",
            get_cmd=self._get_output,
            set_cmd=self._set_output,
            val_mapping={
                "on": "1",
                "off": "0",
                True: "1",
                False: "0",
                "1": "1",
                "0": "0",
                "ON": "1",
                "OFF": "0"
            }
        )

    def _select_channel(self) -> None:
        """选择通道"""
        self.root_instrument._write_retry(f"INST CH{self.channel_id}")
        sleep(0.2)

    def _get_voltage(self) -> float:
        self._select_channel()
        return float(self.root_instrument._ask_retry("VOLT?"))

    def _set_voltage(self, value: float) -> None:
        self._select_channel()
        self.root_instrument._write_retry(f"VOLT {value}")

    def _get_current(self) -> float:
        self._select_channel()
        return float(self.root_instrument._ask_retry("CURR?"))

    def _set_current(self, value: float) -> None:
        self._select_channel()
        self.root_instrument._write_retry(f"CURR {value}")

    def _get_output(self) -> str:
        self._select_channel()
        return self.root_instrument._ask_retry("OUTP?").strip()
        

    def _set_output(self, value) -> None:
        self._select_channel()
        self.root_instrument._write_retry(f"OUTP {value.strip()}")


class DH1766(VisaInstrument):

    RETRY = 3
    RETRY_DELAY = 0.3

    def __init__(self, name: str, address: str, **kwargs):

        super().__init__(name, address, terminator="\n", **kwargs)

        channels = ChannelList(
            parent=self,
            name="channels",
            chan_type=DH1766Channel,
            snapshotable=True,
        )

        for ch in (1, 2, 3):
            channel = DH1766Channel(self, f"ch{ch}", ch)
            channels.append(channel)
            self.add_submodule(f"ch{ch}", channel)

        channels.lock()

        self.add_submodule("channels", channels)

        self.connect_message()
        

    def _ask_retry(self, cmd: str) -> str:

        last_err = None

        for _ in range(self.RETRY):
            try:
                return self.ask(cmd)
            except Exception as e:
                last_err = e
                sleep(self.RETRY_DELAY)

        raise RuntimeError(f"VISA ask failed: {cmd}") from last_err

    def _write_retry(self, cmd: str) -> None:

        last_err = None

        for _ in range(self.RETRY):
            try:
                self.write(cmd)
                return
            except Exception as e:
                last_err = e
                sleep(self.RETRY_DELAY)

        raise RuntimeError(f"VISA write failed: {cmd}") from last_err


