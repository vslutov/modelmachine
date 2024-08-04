"""Test case for input/output device."""

import io

import pytest

from modelmachine.cell import Cell
from modelmachine.io import InputOutputUnit
from modelmachine.memory.ram import RandomAccessMemory

AB = 5
WB = 16


class TestIODevice:
    """Test case for IODevice."""

    ram: RandomAccessMemory
    io_unit: InputOutputUnit

    def setup_method(self) -> None:
        """Init state."""
        self.ram = RandomAccessMemory(address_bits=AB, word_bits=WB)
        self.io_unit = InputOutputUnit(ram=self.ram, io_bits=WB)

    def test_input(self) -> None:
        """Test load data by addresses."""
        with io.StringIO("-123") as fin:
            self.io_unit.input(address=10, message="Slot 10", file=fin)
        assert self.ram.fetch(Cell(10, bits=AB), bits=WB) == -123

        with io.StringIO("-123") as fin, pytest.raises(
            ValueError, match="Unexpected address for input"
        ):
            self.io_unit.input(address=0xFF, file=fin)

        with io.StringIO("0xFFFFFFFFFF") as fin, pytest.raises(
            ValueError, match="Cannot parse integer"
        ):
            self.io_unit.input(address=10, file=fin)

    def test_load_source(self) -> None:
        """Test loading from string."""
        self.io_unit.load_source([(10, "01020A0a10153264")])
        assert self.ram.fetch(Cell(10, bits=AB), bits=WB) == 0x0102
        assert self.ram.fetch(Cell(11, bits=AB), bits=WB) == 0x0A0A
        assert self.ram.fetch(Cell(12, bits=AB), bits=WB) == 0x1015
        assert self.ram.fetch(Cell(13, bits=AB), bits=WB) == 0x3264

    def test_load_source_parse_error(self) -> None:
        with pytest.raises(ValueError, match="Unexpected source"):
            self.io_unit.load_source([(0, "hello")])

        with pytest.raises(
            ValueError, match="Unexpected length of source code"
        ):
            self.io_unit.load_source([(0, "01")])

        self.io_unit.load_source([(0, "0102" * (self.ram.memory_size))])
        with pytest.raises(ValueError, match="Too long source code"):
            self.io_unit.load_source(
                [(0, "0102" * (self.ram.memory_size + 1))]
            )

    def test_load_source_overlaps(self) -> None:
        with pytest.raises(
            ValueError, match=".code directives overlaps at address 0x1"
        ):
            self.io_unit.load_source(
                [(0, "01020A0a10153264"), (1, "01020A0a10153264")]
            )

    def test_store_source(self) -> None:
        """Test save to string method."""
        self.ram.put(address=Cell(20, bits=AB), value=Cell(0x1A10, bits=WB))
        self.ram.put(address=Cell(21, bits=AB), value=Cell(0x1B20, bits=WB))
        self.ram.put(address=Cell(22, bits=AB), value=Cell(0x1C30, bits=WB))

        assert self.io_unit.store_source(start=20, bits=WB) == "1a10"
        assert self.io_unit.store_source(start=21, bits=2 * WB) == "1b20 1c30"

    def test_store_source_assert(self) -> None:
        self.ram.put(address=Cell(0, bits=AB), value=Cell(0xABCD, bits=WB))
        self.ram.put(
            address=Cell((1 << AB) - 1, bits=AB), value=Cell(0xDCBA, bits=WB)
        )
        assert self.io_unit.store_source(start=0, bits=WB) == "abcd"
        assert (
            self.io_unit.store_source(start=(1 << AB) - 1, bits=WB) == "dcba"
        )

        with pytest.raises(AssertionError):
            self.io_unit.store_source(start=0, bits=WB + 1)
        with pytest.raises(AssertionError):
            self.io_unit.store_source(start=-1, bits=WB)
        with pytest.raises(AssertionError):
            self.io_unit.store_source(start=1 << AB, bits=WB)
        with pytest.raises(AssertionError):
            self.io_unit.store_source(start=(1 << AB) - 1, bits=2 * WB)
        with pytest.raises(AssertionError):
            self.io_unit.store_source(start=(1 << AB), bits=WB)

    def test_output(self) -> None:
        """Test load data method."""
        address, value = 0x11, 0x1234
        self.ram.put(
            address=Cell(address, bits=AB), value=Cell(value, bits=WB)
        )
        with io.StringIO() as fout:
            self.io_unit.output(address=address, file=fout)
            assert fout.getvalue() == f"{value}\n"

        self.ram.put(
            address=Cell(address, bits=AB), value=Cell(-value, bits=WB)
        )
        with io.StringIO() as fout:
            self.io_unit.output(address=address, file=fout)
            assert fout.getvalue() == f"{-value}\n"

        with pytest.raises(ValueError, match="Unexpected address"):
            self.io_unit.output(address=0xFF)

        with pytest.raises(ValueError, match="Unexpected address"):
            self.io_unit.output(address=-1)
