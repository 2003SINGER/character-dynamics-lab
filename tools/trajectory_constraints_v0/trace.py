"""Committed evidence trace; no trajectory is inferred between unsupported samples."""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from types import MappingProxyType
from typing import Any, Mapping

from .types import ValueRef, exact_time


@dataclass(frozen=True)
class Point:
    ref: ValueRef
    time: Fraction
    value: Any
    source: str = "committed_projector"
    def __post_init__(self):
        object.__setattr__(self, "time", exact_time(self.time))
        if self.source not in {"committed_projector","world_snapshot_projector","observation_projection","committed_model_state"}:
            raise ValueError("trajectory points must come from a trusted committed projector")


@dataclass(frozen=True)
class Segment:
    """Certified local polynomial or conservative enclosure on [start,end].

    For polynomial, coefficients are ascending powers of (t-start), degree <= 2.
    Bounds are closed enclosures for every point in the interval.
    """
    ref: ValueRef
    start: Fraction
    end: Fraction
    kind: str
    coefficients: tuple[Fraction, ...] = ()
    lower: Fraction | None = None
    upper: Fraction | None = None
    certificate_id: str = ""
    def __post_init__(self):
        object.__setattr__(self, "start", exact_time(self.start))
        object.__setattr__(self, "end", exact_time(self.end))
        if self.end <= self.start:
            raise ValueError("segment must have positive duration")
        if self.kind == "POLYNOMIAL":
            coeff = tuple(Fraction(str(x)) for x in self.coefficients)
            object.__setattr__(self, "coefficients", coeff)
            if not 1 <= len(coeff) <= 3:
                raise ValueError("certified polynomial degree must be 0..2")
            object.__setattr__(self,"coefficients",coeff+(Fraction(0),)*(3-len(coeff)))
        elif self.kind == "BOUNDS":
            if self.lower is None or self.upper is None or self.lower > self.upper:
                raise ValueError("bounds segment requires lower <= upper")
            object.__setattr__(self, "lower", Fraction(str(self.lower)))
            object.__setattr__(self, "upper", Fraction(str(self.upper)))
        else:
            raise ValueError("segment kind must be POLYNOMIAL or BOUNDS")

    def value(self, time: Fraction) -> Fraction:
        if self.kind != "POLYNOMIAL" or not (self.start <= time <= self.end):
            raise ValueError("no certified point value here")
        x = time - self.start
        return sum(c * x**i for i, c in enumerate(self.coefficients))

    def extrema(self, left: Fraction, right: Fraction) -> tuple[Fraction, Fraction]:
        if self.kind != "POLYNOMIAL":
            raise ValueError("generic bounds do not expose exact extrema")
        a, b = max(left, self.start), min(right, self.end)
        candidates = [self.value(a), self.value(b)]
        if len(self.coefficients) == 3 and self.coefficients[2] != 0:
            vertex = self.start - self.coefficients[1] / (2 * self.coefficients[2])
            if a < vertex < b:
                candidates.append(self.value(vertex))
        return min(candidates), max(candidates)

    def integral(self, left: Fraction, right: Fraction) -> Fraction:
        if self.kind != "POLYNOMIAL":
            raise ValueError("bounds segment has no exact integral")
        a, b = max(left, self.start) - self.start, min(right, self.end) - self.start
        return sum(c * (b**(i + 1) - a**(i + 1)) / (i + 1) for i, c in enumerate(self.coefficients))


@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    time: Fraction
    sequence: int
    args: Mapping[str, Any] = field(default_factory=dict)
    version: str = "1"
    provenance: str = "committed_ledger"
    def __post_init__(self):
        object.__setattr__(self, "time", exact_time(self.time))
        object.__setattr__(self,"args",MappingProxyType(dict(self.args)))
        if self.time < 0 or self.sequence < 0 or not self.event_id or not self.event_type:
            raise ValueError("invalid event identity, timestamp, or sequence")
        if self.provenance not in {"committed_ledger","delivered_observation","initial_evidence"}:
            raise ValueError("event provenance is not an admitted committed source")


class Trace:
    def __init__(self, *, scenario_start: Fraction = Fraction(0), now: Fraction = Fraction(0)):
        self.scenario_start = exact_time(scenario_start)
        self.now = exact_time(now)
        self.points: list[Point] = []
        self.segments: list[Segment] = []
        self.events: list[Event] = []
        self.tombstones: set[str] = set()
        self.tombstone_times: dict[str,Fraction] = {}
        self._values_sealed_through: dict[tuple, Fraction] = {}
        self._event_ids: dict[str, Event] = {}
        self._event_keys: dict[tuple[Fraction,int],str] = {}
        self._events_sealed_through: Fraction | None = None
        self._events_finalized = False

    def advance(self, now: int | str | Fraction) -> None:
        now = exact_time(now)
        if self._events_finalized and now!=self.now: raise ValueError("cannot advance a finalized trace")
        if now < self.now:
            raise ValueError("trace time cannot move backwards")
        self.now = now

    def add_point(self, point: Point) -> None:
        if point.time < self.scenario_start or point.time > self.now:
            raise ValueError("point timestamp outside committed trace")
        old=[p for p in self.points if p.ref==point.ref and p.time==point.time]
        if old:
            if old[-1]!=point: raise ValueError("conflicting same-reference point at same timestamp")
            return
        seal=self.values_sealed_through(point.ref)
        if seal is not None and point.time<=seal:
            raise ValueError("cannot append a point behind the sealed value frontier")
        for seg in self.segments:
            if seg.ref!=point.ref or not seg.start<=point.time<=seg.end: continue
            value=Fraction(str(point.value))
            if seg.kind=="POLYNOMIAL" and value!=seg.value(point.time): raise ValueError("point contradicts certified polynomial segment")
            if seg.kind=="BOUNDS" and not seg.lower<=value<=seg.upper: raise ValueError("point contradicts certified interval bounds")
        self.points.append(point)

    def add_segment(self, segment: Segment) -> None:
        if segment.start < self.scenario_start or segment.end > self.now:
            raise ValueError("segment outside committed trace")
        seal=self.values_sealed_through(segment.ref)
        if seal is not None and segment.start<=seal:
            raise ValueError("cannot append a segment behind the sealed value frontier")
        if any(s.ref==segment.ref and s.start<segment.end and segment.start<s.end for s in self.segments):
            raise ValueError("overlapping certificates for the same reference are rejected")
        for point in self.points:
            if point.ref!=segment.ref or not segment.start<=point.time<=segment.end: continue
            value=Fraction(str(point.value))
            if segment.kind=="POLYNOMIAL" and value!=segment.value(point.time): raise ValueError("segment contradicts existing point")
            if segment.kind=="BOUNDS" and not segment.lower<=value<=segment.upper: raise ValueError("bounds contradict existing point")
        self.segments.append(segment)

    def add_event(self, event: Event) -> None:
        if event.time < self.scenario_start or event.time > self.now:
            raise ValueError("event timestamp outside committed trace")
        old = self._event_ids.get(event.event_id)
        if old is not None:
            if old != event:
                raise ValueError(f"conflicting duplicate event id: {event.event_id}")
            return  # exact duplicate is counted once
        if self._events_sealed_through is not None and event.time <= self._events_sealed_through:
            raise ValueError("cannot append an event behind the sealed ledger frontier")
        if self._events_finalized: raise ValueError("cannot append to finalized event ledger")
        if self.events and (event.time, event.sequence) < (self.events[-1].time, self.events[-1].sequence):
            raise ValueError("reordered committed events are rejected")
        key=(event.time,event.sequence)
        if key in self._event_keys: raise ValueError("ledger (time, sequence) order key must be unique")
        self._event_ids[event.event_id] = event
        self._event_keys[key]=event.event_id
        self.events.append(event)

    def seal_events_through(self, time: int | str | Fraction) -> None:
        """Declare authoritative ledger completeness from scenario start through time."""
        time=exact_time(time)
        if time<self.scenario_start or time>self.now: raise ValueError("invalid event completeness frontier")
        if self._events_sealed_through is not None and time<self._events_sealed_through:
            raise ValueError("event completeness frontier cannot move backwards")
        self._events_sealed_through=time

    def finalize_events(self, through: int | str | Fraction | None = None) -> None:
        self.seal_events_through(self.now if through is None else through)
        self._events_finalized=True

    @property
    def events_sealed_through(self) -> Fraction | None:
        return self._events_sealed_through

    @property
    def events_finalized(self) -> bool:
        return self._events_finalized

    def delete_entity(self, stable_id: str, at: int | str | Fraction | None = None) -> None:
        self.tombstones.add(stable_id)
        when=self.now if at is None else exact_time(at)
        if when<self.scenario_start or when>self.now: raise ValueError("tombstone time outside committed trace")
        self.tombstone_times[stable_id]=when

    def is_tombstoned(self, stable_id: str, at: Fraction) -> bool:
        when=self.tombstone_times.get(stable_id)
        return when is not None and when<=at

    def values(self, ref: ValueRef) -> list[Point]:
        return sorted((p for p in self.points if p.ref == ref), key=lambda p: p.time)

    def seal_values_through(self, ref: ValueRef, time: int | str | Fraction) -> None:
        """Declare the committed step-signal history complete through `time`."""
        time=exact_time(time)
        if time<self.scenario_start or time>self.now: raise ValueError("invalid value completeness frontier")
        key=ref.dependency_key
        if key in self._values_sealed_through and time<self._values_sealed_through[key]:
            raise ValueError("value completeness frontier cannot move backwards")
        self._values_sealed_through[key]=time

    def values_sealed_through(self, ref: ValueRef) -> Fraction | None:
        return self._values_sealed_through.get(ref.dependency_key)

    def matching_events(self, event_type: str, filters: Mapping[str, Any] | None = None, version: str | None = None) -> list[Event]:
        filters = filters or {}
        def match(e,k,v): return e.event_id==v if k=="event_id" else e.args.get(k)==v
        return [e for e in self.events if e.event_type == event_type and (version is None or e.version==version) and all(match(e,k,v) for k,v in filters.items())]
