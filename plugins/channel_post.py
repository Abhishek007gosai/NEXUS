"""Automatic File Store ingestion is disabled.

Channel posts/files are NOT automatically saved to MongoDB or copied to a
database channel. File Store persistence and link generation happen only
through the explicit /genlink and /batch commands.
"""
# Intentionally no message handler in this module.
