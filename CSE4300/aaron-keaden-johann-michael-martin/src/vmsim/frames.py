"""Physical frame allocation and ownership tracking."""


class FrameTable:
    """Track allocated physical frames and their owning virtual pages."""

    def __init__(self, num_frames: int) -> None:
        if num_frames < 0:
            raise ValueError("num_frames must be non-negative")
        self._allocated = [False] * num_frames
        self._owners: list[tuple[int, int] | None] = [None] * num_frames

    def _check_frame(self, frame: int) -> None:
        if not 0 <= frame < len(self._allocated):
            raise IndexError(f"frame index out of range: {frame}")

    def alloc(self) -> int | None:
        """Reserve and return the first free frame, or None if full."""
        for frame, allocated in enumerate(self._allocated):
            if not allocated:
                self._allocated[frame] = True
                return frame
        return None

    def free(self, frame: int) -> None:
        """Release a frame and clear its owner."""
        self._check_frame(frame)
        self._allocated[frame] = False
        self._owners[frame] = None

    def owner(self, frame: int) -> tuple[int, int]:
        """Return the process and VPN owning frame."""
        self._check_frame(frame)
        owner = self._owners[frame]
        if owner is None:
            raise ValueError(f"frame {frame} has no owner")
        return owner

    def set_owner(self, frame: int, pid: int, vpn: int) -> None:
        """Set the owner of an allocated frame."""
        self._check_frame(frame)
        self._allocated[frame] = True
        self._owners[frame] = (pid, vpn)
