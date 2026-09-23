# 508 Transportation Planning

Reproducible Python project environment for CME 508 Transportation Planning coursework.

The project uses Python 3.12 and `uv` for dependency and virtual-environment management.

Export a notebook from the project root (PowerShell):

```powershell
.\.venv\Scripts\python.exe scripts/export_homework.py notebooks/Homework_2.ipynb
```

Replace the last argument with the path to another `.ipynb` file; quote paths
containing spaces. The script executes the notebook in memory from the project
root and saves `reports/<notebook-name>.html` and `reports/<notebook-name>.pdf`.
Existing reports with the same name are replaced; the source notebook is not
modified. Chrome or Edge is required for PDF export. Without an argument, the
script exports `notebooks/homework_1.ipynb` as before.

