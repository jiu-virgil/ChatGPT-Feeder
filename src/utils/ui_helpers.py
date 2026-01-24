"""UI helper utilities."""
from PySide6.QtWidgets import QComboBox


def update_dropdown_arrow_visibility(combo: QComboBox) -> None:
    """Show or hide the dropdown arrow based on whether there are items.
    
    Args:
        combo: QComboBox widget to update
    """
    if combo.count() == 0:
        # Hide the dropdown arrow
        combo.setStyleSheet("QComboBox::drop-down { border: none; width: 0px; }")
    else:
        # Show the dropdown arrow (reset to default)
        combo.setStyleSheet("")


