"""
CSV output module for logging data to CSV files.

Provides structured logging with automatic header management.
Works headless - no display required.
"""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class CSVWriter:
    """
    CSV writer for logging extracted data to files.

    Automatically manages headers and handles schema evolution.

    Example:
        >>> csv_out = CSVWriter("readings.csv")
        >>> csv_out.append({"temperature": 185.5, "pressure": 42.3})
        >>> csv_out.append({"temperature": 186.0, "pressure": 42.1})
    """

    def __init__(
        self,
        filepath: Union[str, Path],
        fieldnames: Optional[List[str]] = None,
        add_timestamp: bool = True,
        timestamp_format: str = "%Y-%m-%d %H:%M:%S",
        delimiter: str = ",",
        append_mode: bool = True,
    ):
        """
        Initialize CSV writer.

        Args:
            filepath: Path to CSV file.
            fieldnames: Optional list of column names. Auto-detected if not provided.
            add_timestamp: Whether to add a timestamp column.
            timestamp_format: Format string for timestamps.
            delimiter: CSV delimiter character.
            append_mode: If True, append to existing file. If False, overwrite.
        """
        self.filepath = Path(filepath)
        self.fieldnames = fieldnames
        self.add_timestamp = add_timestamp
        self.timestamp_format = timestamp_format
        self.delimiter = delimiter
        self.append_mode = append_mode

        # Track if headers have been written
        self._headers_written = False

        # Ensure parent directory exists
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

        # Check for existing file
        if self.filepath.exists() and self.append_mode:
            self._read_existing_headers()

    def _read_existing_headers(self) -> None:
        """Read headers from existing file."""
        try:
            with open(self.filepath, "r", newline="") as f:
                reader = csv.reader(f, delimiter=self.delimiter)
                first_row = next(reader, None)
                if first_row:
                    self.fieldnames = first_row
                    self._headers_written = True
        except Exception:
            pass

    def append(
        self,
        data: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Append a row of data to the CSV file.

        Args:
            data: Dictionary of field names to values.
            timestamp: Optional timestamp. Uses current time if not provided.
        """
        # Add timestamp if configured
        row_data = dict(data)
        if self.add_timestamp:
            ts = timestamp or datetime.now()
            row_data["timestamp"] = ts.strftime(self.timestamp_format)

        # Determine fieldnames if not set
        if self.fieldnames is None:
            # Put timestamp first if present
            if self.add_timestamp:
                self.fieldnames = ["timestamp"] + [k for k in row_data.keys() if k != "timestamp"]
            else:
                self.fieldnames = list(row_data.keys())

        # Check for new fields
        new_fields = set(row_data.keys()) - set(self.fieldnames)
        if new_fields:
            # Add new fields to end
            self.fieldnames.extend(sorted(new_fields))
            # Need to rewrite file if headers already written
            if self._headers_written:
                self._rewrite_with_new_headers()

        # Write to file
        mode = "a" if self._headers_written else "w"
        with open(self.filepath, mode, newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=self.fieldnames,
                delimiter=self.delimiter,
                extrasaction="ignore",
            )

            # Write header if needed
            if not self._headers_written:
                writer.writeheader()
                self._headers_written = True

            writer.writerow(row_data)

    def append_batch(
        self,
        readings: List[Dict[str, Any]],
    ) -> int:
        """
        Append multiple rows at once.

        Args:
            readings: List of data dictionaries.

        Returns:
            Number of rows written.
        """
        for data in readings:
            self.append(data)
        return len(readings)

    def _rewrite_with_new_headers(self) -> None:
        """Rewrite file with updated headers."""
        # Read existing data
        rows = []
        with open(self.filepath, "r", newline="") as f:
            reader = csv.DictReader(f, delimiter=self.delimiter)
            for row in reader:
                rows.append(row)

        # Write with new headers
        with open(self.filepath, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=self.fieldnames,
                delimiter=self.delimiter,
                extrasaction="ignore",
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def read_all(self) -> List[Dict[str, str]]:
        """
        Read all rows from the CSV file.

        Returns:
            List of row dictionaries.
        """
        if not self.filepath.exists():
            return []

        rows = []
        with open(self.filepath, "r", newline="") as f:
            reader = csv.DictReader(f, delimiter=self.delimiter)
            for row in reader:
                rows.append(dict(row))

        return rows

    def get_row_count(self) -> int:
        """Get the number of data rows in the file (excluding header)."""
        if not self.filepath.exists():
            return 0

        with open(self.filepath, "r", newline="") as f:
            count = sum(1 for _ in f) - 1  # Subtract header row
            return max(0, count)  # Never return negative

    def clear(self) -> None:
        """Clear the CSV file (remove all data but keep headers)."""
        if self.fieldnames:
            with open(self.filepath, "w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=self.fieldnames,
                    delimiter=self.delimiter,
                )
                writer.writeheader()
            self._headers_written = True
        else:
            # Just delete the file
            if self.filepath.exists():
                os.remove(self.filepath)
            self._headers_written = False

    def get_latest(self, n: int = 1) -> List[Dict[str, str]]:
        """
        Get the latest N rows from the file.

        Args:
            n: Number of rows to retrieve.

        Returns:
            List of row dictionaries (most recent first).
        """
        rows = self.read_all()
        return rows[-n:][::-1]

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass  # No cleanup needed for file-based writer
