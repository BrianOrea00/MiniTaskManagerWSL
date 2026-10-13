"""Embedded matplotlib canvas."""

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ..theme import DARK_BG


class MplCanvas(FigureCanvas):
    """A matplotlib canvas sized for the overview chart."""

    def __init__(self, parent=None, width: float = 8, height: float = 2.5, dpi: int = 100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

        self.fig.patch.set_facecolor(DARK_BG)
        self.ax.set_facecolor(DARK_BG)
        self.ax.set_xlabel("Time (seconds)", color="white", fontsize=9)
        self.ax.set_ylabel("Usage %", color="white", fontsize=9)
        self.ax.tick_params(colors="white", labelsize=8)
        self.ax.grid(True, alpha=0.3, color="gray")
