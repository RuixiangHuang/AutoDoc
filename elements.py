"""
Shared helpers for identifying code elements across the pipeline.

Kept dependency-free so it can be imported (and tested) without LLM or
vector-store packages installed.
"""
from typing import Dict, Optional


def element_id(file: str, element_type: str, name: str, class_name: Optional[str] = "") -> str:
    """
    Unique key for a class or function.

    `file` is the path relative to the scanned root, so same-named files in
    different directories don't collide; `class_name` disambiguates methods
    with the same name in different classes.
    """
    qualified = f"{class_name}.{name}" if class_name else name
    return f"{file}::{element_type}::{qualified}"


def is_same_element(
    metadata: Dict,
    file: str,
    element_type: str,
    name: str,
    class_name: Optional[str] = "",
) -> bool:
    """True if a vector-store result's metadata refers to the given element."""
    return (
        metadata.get("file") == file
        and metadata.get("type") == element_type
        and metadata.get("name") == name
        and (metadata.get("class_name") or "") == (class_name or "")
    )
