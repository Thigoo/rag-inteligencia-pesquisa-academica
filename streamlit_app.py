"""
Ponto de entrada raiz para a aplicação Streamlit.
Executa a interface definida em app/streamlit_app.py.
"""
from pathlib import Path
import runpy

app_path = Path(__file__).resolve().parent / "app" / "streamlit_app.py"
runpy.run_path(str(app_path), run_name="__main__")
