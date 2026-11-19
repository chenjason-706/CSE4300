"""Page-replacement policies for the virtual memory simulator."""

from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict, deque
from collections.abc import Iterable

Page = tuple[int, int]  # (process ID, virtual page number)


class Policy(ABC):
    """Common frame-based interface used by the MMU."""

    def __init__(self, num_frames: int) -> None:
        if num_frames <= 0:
            raise ValueError("num_frames must be positive")
        self.num_frames = num_frames

    def _check_frame(self, frame: int) -> None:
        if not 0 <= frame < self.num_frames:
            raise ValueError(f"Invalid frame: {frame}")

    @abstractmethod
    def on_load(self, frame: int) -> None:
        """Record that a new page occupies this frame."""

    @abstractmethod
    def on_access(self, frame: int) -> None:
        """Record every memory access, including TLB hits."""

    @abstractmethod
    def on_evict(self, frame: int) -> None:
        """Forget the page currently occupying this frame."""

    @abstractmethod
    def choose_victim(self) -> int:
        """Select an occupied frame; the MMU performs the eviction."""


class FIFOPolicy(Policy):
    """First In, First Out: track page arrival order."""

    def __init__(self, num_frames: int) -> None:
        super().__init__(num_frames)
        self.queue: deque[int] = deque()

    def on_load(self, frame: int) -> None:
        self._check_frame(frame)
        if frame in self.queue:
            raise ValueError("Frame is already loaded")
        self.queue.append(frame)

    def on_access(self, frame: int) -> None:
        # FIFO ignores access order.
        pass

    def on_evict(self, frame: int) -> None:
        self.queue.remove(frame)

    def choose_victim(self) -> int:
        if not self.queue:
            raise RuntimeError("No occupied frames")
        return self.queue[0]


class LRUPolicy(Policy):
    """Least Recently Used: track the order of accesses."""

    def __init__(self, num_frames: int) -> None:
        super().__init__(num_frames)
        self.order: OrderedDict[int, None] = OrderedDict()

    def on_load(self, frame: int) -> None:
        self._check_frame(frame)
        if frame in self.order:
            raise ValueError("Frame is already loaded")
        self.order[frame] = None

    def on_access(self, frame: int) -> None:
        # Move the accessed frame from its old position to the newest end.
        self.order.move_to_end(frame)

    def on_evict(self, frame: int) -> None:
        del self.order[frame]

    def choose_victim(self) -> int:
        if not self.order:
            raise RuntimeError("No occupied frames")
        return next(iter(self.order))


class ClockPolicy(Policy):
    """Second Chance: scan circularly and clear reference bits."""

    def __init__(self, num_frames: int) -> None:
        super().__init__(num_frames)
        self.referenced: dict[int, bool] = {}
        self.hand = 0

    def on_load(self, frame: int) -> None:
        self._check_frame(frame)
        if frame in self.referenced:
            raise ValueError("Frame is already loaded")
        # The upcoming on_access call will set this bit.
        self.referenced[frame] = False

    def on_access(self, frame: int) -> None:
        if frame not in self.referenced:
            raise ValueError("Frame is not loaded")
        self.referenced[frame] = True

    def on_evict(self, frame: int) -> None:
        del self.referenced[frame]

    def choose_victim(self) -> int:
        if not self.referenced:
            raise RuntimeError("No occupied frames")
        while True:
            frame = self.hand
            self.hand = (self.hand + 1) % self.num_frames
            if frame not in self.referenced:
                continue
            if not self.referenced[frame]:
                return frame
            # Give this frame another chance on the next lap.
            self.referenced[frame] = False


class OPTPolicy(Policy):
    """Optimal offline replacement: evict the farthest next use."""

    def __init__(self, num_frames: int, future: Iterable[Page]) -> None:
        super().__init__(num_frames)
        self.future = list(future)
        self.position = 0
        self.resident: dict[int, Page] = {}
        self.next_uses: dict[Page, deque[int]] = defaultdict(deque)
        for index, page in enumerate(self.future):
            self.next_uses[page].append(index)

    def _current_page(self) -> Page:
        if self.position >= len(self.future):
            raise RuntimeError("OPT received more accesses than its trace")
        return self.future[self.position]

    def on_load(self, frame: int) -> None:
        self._check_frame(frame)
        if frame in self.resident:
            raise ValueError("Frame is already loaded")
        # The MMU loads the current requested page BEFORE on_access.
        self.resident[frame] = self._current_page()

    def on_access(self, frame: int) -> None:
        page = self._current_page()
        if self.resident.get(frame) != page:
            raise RuntimeError("OPT trace and MMU access order disagree")
        positions = self.next_uses[page]
        if not positions or positions[0] != self.position:
            raise RuntimeError("OPT future-use index is out of sync")
        positions.popleft()
        self.position += 1

    def on_evict(self, frame: int) -> None:
        del self.resident[frame]

    def choose_victim(self) -> int:
        if not self.resident:
            raise RuntimeError("No occupied frames")

        def next_use(frame: int) -> float:
            positions = self.next_uses[self.resident[frame]]
            return positions[0] if positions else float("inf")

        # Prefer the lowest frame number when next-use times tie.
        return max(self.resident, key=lambda frame: (next_use(frame), -frame))


def make_policy(
    name: str, num_frames: int, future: Iterable[Page] | None = None
) -> Policy:
    """Create a replacement policy by name using the team's interface."""
    name = name.lower()
    if name == "fifo":
        return FIFOPolicy(num_frames)
    if name == "lru":
        return LRUPolicy(num_frames)
    if name == "clock":
        return ClockPolicy(num_frames)
    if name == "opt":
        if future is None:
            raise ValueError("OPT requires the complete ordered access trace")
        return OPTPolicy(num_frames, future)
    raise ValueError(f"Unknown replacement policy: {name}")
