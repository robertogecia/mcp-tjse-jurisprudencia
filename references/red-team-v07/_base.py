import os, sys, tempfile
os.environ.setdefault("TJSE_DIR_DADOS", tempfile.mkdtemp())
sys.path.insert(0, os.path.expanduser("~/MCP/tjse-jurisprudencia"))
import servidor_tjse as S  # noqa
