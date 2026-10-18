"""Prepara una copia distribuible, sin publicar ni enviar credenciales."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'output/publicacion/STE_Calculator'


def main():
    files=[ROOT/name for name in ('app.py','requirements.txt','requirements-lock.txt',
                                 'README.md','VERIFICACION.md','iniciar.bat','iniciar.ps1','.gitignore')]
    for folder in ('ste_calculator','scripts','tests'):
        files.extend(p for p in (ROOT/folder).rglob('*.py') if '__pycache__' not in p.parts)
    files.extend(p for p in (ROOT/'referencias').rglob('*') if p.is_file() and p.suffix.lower() in ('.md','.json','.txt'))
    manifest={}
    for source in sorted(files):
        relative=source.relative_to(ROOT)
        target=DEST/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        manifest[relative.as_posix()]=hashlib.sha256(target.read_bytes()).hexdigest()
    config=ROOT/'.streamlit/config.toml'
    target=DEST/'.streamlit/config.toml'
    target.parent.mkdir(parents=True,exist_ok=True)
    # La copia local conserva 127.0.0.1. En la nube la dirección la decide el host.
    target.write_text('\n'.join(line for line in config.read_text(encoding='utf-8').splitlines()
                               if not line.strip().startswith('address ='))+'\n',encoding='utf-8')
    manifest['.streamlit/config.toml']=hashlib.sha256(target.read_bytes()).hexdigest()
    (DEST/'PUBLICACION.md').write_text('''# Distribución pública

Esta copia contiene el código actual, pruebas, catálogo y datos de comparación.
No incluye PDF de libros/apuntes, credenciales, entorno virtual ni resultados locales.
Las fuentes permanecen identificadas; cada lector puede añadir copias autorizadas.

## Streamlit Community Cloud

Repositorio previsto: pguerrero-sys/STE_Calculator. Archivo principal: app.py.
Seleccionar Python 3.12. Las dependencias están en requirements.txt.
Los PDF se generan en memoria, sin programas externos de Windows.
La configuración de red pública queda a cargo del host; la copia local no cambia.

Descargar el ZIP desde Code > Download ZIP en GitHub, extraerlo y seguir README.md.
El ZIP no es un ejecutable: para ejecutarlo localmente se necesita Python.
''',encoding='utf-8')
    (DEST/'PUBLICATION_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    archive=DEST.parent/'STE_Calculator.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(DEST.rglob('*')):
            if path.is_file() and '.git' not in path.relative_to(DEST).parts:
                z.write(path,Path('STE_Calculator')/path.relative_to(DEST))
    print(f'{len(manifest)} archivos preparados; ZIP: {archive}')


if __name__=='__main__':
    main()
