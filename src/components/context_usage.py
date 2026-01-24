"""Context usage display widget with gauge indicators."""

import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.utils.tokens import (
    CURSOR_CONTEXT,
    GEMINI_3_PRO_CONTEXT,
    GPT_4_1_CONTEXT,
    GPT_5_CONTEXT,
    format_percentage,
)


class GaugeDisplayWidget(QWidget):
    """Widget that displays a semi-circular gauge."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._percentage = 0.0
        self.setFixedSize(100, 60)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def set_percentage(self, percentage: float) -> None:
        """Set the gauge percentage."""
        self._percentage = percentage
        self.update()

    def paintEvent(self, event):
        """Paint the gauge."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        width = rect.width()
        height = rect.height()

        # Draw semi-circular gauge
        center_x = width // 2
        center_y = height
        radius = min(width, height * 2) // 2 - 5

        # Background arc (gray) - full semi-circle from left (180°) to right (0°)
        pen = QPen(QColor(100, 100, 100), 8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        # Start at 180° (left), span -180° (clockwise to right)
        painter.drawArc(
            center_x - radius,
            center_y - radius,
            radius * 2,
            radius * 2,
            180 * 16,
            -180 * 16,
        )

        # Determine color based on percentage
        if self._percentage <= 50:
            color = QColor(76, 175, 80)  # Green
        elif self._percentage <= 80:
            color = QColor(255, 193, 7)  # Yellow
        elif self._percentage <= 100:
            color = QColor(244, 67, 54)  # Red
        else:
            color = QColor(156, 39, 176)  # Dark red/purple for over limit

        # Foreground arc (colored based on percentage)
        # Fill from left (180°) to right based on percentage
        if self._percentage > 0:
            pen = QPen(color, 8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            # Start at 180° (left), span negative angle (clockwise) based on percentage
            # Cap at 100% for visual display (over 100% still shows full)
            display_pct = min(self._percentage, 100.0)
            span_angle = int(-(display_pct / 100.0) * 180 * 16)
            painter.drawArc(
                center_x - radius,
                center_y - radius,
                radius * 2,
                radius * 2,
                180 * 16,
                span_angle,
            )

            # Draw center indicator line pointing to the end of the filled arc
            # Calculate the end angle: 180° - (percentage * 180° / 100°)
            end_angle_deg = 180 - (display_pct / 100.0) * 180
            angle_rad = math.radians(end_angle_deg)
            end_x = center_x + int(radius * math.cos(angle_rad))
            end_y = center_y - int(radius * math.sin(angle_rad))

            pen = QPen(color, 2)
            painter.setPen(pen)
            painter.drawLine(center_x, center_y, end_x, end_y)

        painter.end()


class GaugeWidget(QWidget):
    """Single gauge indicator widget."""

    def __init__(self, model_name: str, context_limit: int, parent=None):
        super().__init__(parent)
        self._model_name = model_name
        self._context_limit = context_limit
        self._percentage = 0.0

        # Set fixed width to prevent movement
        self.setFixedWidth(120)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Model name label
        self._name_label = QLabel(model_name)
        self._name_label.setAlignment(Qt.AlignCenter)
        self._name_label.setStyleSheet("font-weight: 600; font-size: 9pt;")
        layout.addWidget(self._name_label)

        # Gauge (semi-circular)
        self._gauge_display = GaugeDisplayWidget()
        layout.addWidget(self._gauge_display, alignment=Qt.AlignCenter)

        # Percentage info (no token count)
        self._info_label = QLabel("0%")
        self._info_label.setAlignment(Qt.AlignCenter)
        self._info_label.setStyleSheet("font-size: 8pt; color: palette(window-text);")
        layout.addWidget(self._info_label)

        self.setLayout(layout)

    def update_usage(self, tokens: int, percentage: float) -> None:
        """Update gauge with new token count and percentage."""
        self._percentage = percentage

        # Update gauge display
        self._gauge_display.set_percentage(percentage)

        # Update info label (percentage only, no token count)
        pct_str = format_percentage(percentage)
        if percentage > 100:
            self._info_label.setText(f"{pct_str} (OVER LIMIT)")
            self._info_label.setStyleSheet(
                "font-size: 8pt; color: #ff0000; font-weight: 600;"
            )
        else:
            self._info_label.setText(pct_str)
            self._info_label.setStyleSheet(
                "font-size: 8pt; color: palette(window-text);"
            )


class ContextUsageWidget(QWidget):
    """Widget displaying context usage for multiple models with gauge indicators."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Title (centered)
        title = QLabel("Context Usage")
        title.setStyleSheet("font-weight: 600; font-size: 10pt; padding-bottom: 4px;")
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Modern separator with subtle styling
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Plain)
        separator.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        separator.setStyleSheet(
            """
            QFrame {
                border: none;
                border-top: 1px solid palette(mid);
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent, stop:0.5 palette(mid), stop:1 transparent);
                max-height: 1px;
            }
        """
        )
        layout.addWidget(separator)

        # Gauges in a horizontal layout (centered)
        gauges_layout = QHBoxLayout()
        gauges_layout.setSpacing(12)
        gauges_layout.setContentsMargins(0, 0, 0, 0)

        # Add stretch before gauges to center them
        gauges_layout.addStretch()

        # Create gauge for each model
        self._cursor_gauge = GaugeWidget("Cursor", CURSOR_CONTEXT)
        self._gpt5_gauge = GaugeWidget("GPT-5", GPT_5_CONTEXT)
        self._gpt41_gauge = GaugeWidget("GPT-4.1", GPT_4_1_CONTEXT)
        self._gemini_gauge = GaugeWidget("Gemini 3 Pro", GEMINI_3_PRO_CONTEXT)

        gauges_layout.addWidget(self._cursor_gauge)
        gauges_layout.addWidget(self._gpt5_gauge)
        gauges_layout.addWidget(self._gpt41_gauge)
        gauges_layout.addWidget(self._gemini_gauge)

        # Add stretch after gauges to center them
        gauges_layout.addStretch()

        layout.addLayout(gauges_layout)
        self.setLayout(layout)

    def update_usage(
        self,
        tokens: int,
        cursor_pct: float,
        gpt5_pct: float,
        gpt41_pct: float,
        gemini_pct: float,
    ) -> None:
        """Update all gauges with new usage data."""
        self._cursor_gauge.update_usage(tokens, cursor_pct)
        self._gpt5_gauge.update_usage(tokens, gpt5_pct)
        self._gpt41_gauge.update_usage(tokens, gpt41_pct)
        self._gemini_gauge.update_usage(tokens, gemini_pct)

    def clear_usage(self) -> None:
        """Clear all gauges to zero."""
        self.update_usage(0, 0.0, 0.0, 0.0, 0.0)  # tokens, cursor, gpt5, gpt41, gemini
