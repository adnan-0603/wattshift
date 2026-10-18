"""Execute notebook cells in-process when kernel sockets are unavailable."""
from pathlib import Path
import nbformat
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output
root=Path(__file__).resolve().parents[1];p=root/'notebooks/01-understand-energy.ipynb'
n=nbformat.read(p,as_version=4);shell=InteractiveShell.instance();count=0
for cell in n.cells:
 if cell.cell_type!='code':continue
 count+=1
 with capture_output() as captured:result=shell.run_cell(cell.source)
 result.raise_error();cell.execution_count=count;cell.outputs=[]
 if captured.stdout:cell.outputs.append(nbformat.v4.new_output('stream',name='stdout',text=captured.stdout))
 for output in captured.outputs:cell.outputs.append(nbformat.v4.new_output('display_data',data=output.data,metadata=output.metadata))
n.metadata['wattshift_verification']='Code cells executed in-process with IPython; network kernel not used.'
nbformat.write(n,p);print(f'{count} notebook code cells executed in-process successfully.')
