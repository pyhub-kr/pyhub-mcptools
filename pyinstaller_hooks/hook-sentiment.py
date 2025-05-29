"""PyInstaller hook for sentiment analysis tool."""

from PyInstaller.utils.hooks import collect_data_files

# Collect sentiment data files (Korean dictionaries)
datas = collect_data_files('pyhub.mcptools.sentiment.data')