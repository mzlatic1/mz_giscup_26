"""Small integer-bitset abstraction used by greedy coverage routines."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IntBitSet:
    bits: int = 0

    @classmethod
    def from_ids(cls, ids: set[int] | list[int] | tuple[int, ...]) -> "IntBitSet":
        bits = 0
        for idx in ids:
            bits |= 1 << int(idx)
        return cls(bits)

    def union(self, other: "IntBitSet") -> "IntBitSet":
        return IntBitSet(self.bits | other.bits)

    def intersection(self, other: "IntBitSet") -> "IntBitSet":
        return IntBitSet(self.bits & other.bits)

    def difference(self, other: "IntBitSet") -> "IntBitSet":
        return IntBitSet(self.bits & ~other.bits)

    def count(self) -> int:
        return self.bits.bit_count()

    def iter_set_bits(self):
        bits = self.bits
        while bits:
            lowest = bits & -bits
            yield lowest.bit_length() - 1
            bits ^= lowest
