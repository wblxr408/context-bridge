"""Windows UTF-8 entrypoint for the extended, existing Basic Memory bridge."""
import os
from pathlib import Path
import sys
home=Path(os.environ.get('ENGINEERING_MEMORY_HOME') or Path.home()/'.codex/services/engineering-memory')
sys.path.insert(0,str(home/'app'))
from mcp_proxy import main
if __name__=='__main__':main()
