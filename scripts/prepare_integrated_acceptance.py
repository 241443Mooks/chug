"""Prepare only. Never imported by the matcher or the HTTP verification runner."""
from pathlib import Path
import json,zipfile,hashlib,html,sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chug.document import extract_file
import argparse
parser = argparse.ArgumentParser(description='Prepare synthetic sources and a separate withheld key; run the HTTP verifier before evaluating it.')
parser.add_argument('--workspace', type=Path, required=True)
args = parser.parse_args()
root=ROOT; lib=root/'research/reference-library-v0.1'; out=args.workspace.resolve();out.mkdir(parents=True, exist_ok=False)
refs=json.loads((lib/'catalog.json').read_text())['references']
# Freeze these expectations before executing the integrated matcher.
expected=[('C001','NDA-UK-EVAL'),('C004','NDA-UK-SUPPLIER'),('C007','NDA-UK-ONEWAY'),('C009','ORDER-PRO-DIRECT'),('C012','ORDER-DAST-CLOUD'),('C015','ORDER-DAST-SELF'),('C017','ORDER-COMBINED'),('C019','ORDER-RESELLER')]
manifest={'references':[str(lib/r['file']) for r in refs], 'files':[]};key=[]
# Fixed opaque identifiers deliberately do not encode family or expected reference.
labels=['q7','m2','v9','h4','t8','a3','z6','d1','r5','x0']
def docx(paragraphs,path):
 body=''.join('<w:p><w:r><w:t xml:space="preserve">'+html.escape(p)+'</w:t></w:r></w:p>' for p in paragraphs)
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
  def write(name, data):
   entry=zipfile.ZipInfo(name, (2026, 10, 19, 0, 0, 0));entry.compress_type=zipfile.ZIP_DEFLATED;z.writestr(entry, data)
  write('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
  write('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
  write('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'</w:body></w:document>')
for i,(prefix,refid) in enumerate(expected):
 src=next((lib/'routine-clients').glob(prefix+'*.docx'))
 # Rebuild rather than edit ZIP: removes core/custom properties, header/footer metadata,
 # source filename and stale relationships. Retain the ordinary agreement title and clauses.
 paragraphs=[u['text'] for u in extract_file(src)['units'] if not u['text'].startswith(('Standard family:','Document ID:'))]
 p=out/(labels[i]+'.docx');docx(paragraphs,p)
 # Scan every ZIP member, not only visible body paragraphs, for answer IDs/hints.
 with zipfile.ZipFile(p) as z:
  whole=b' '.join(z.read(n) for n in z.namelist())
  assert not any(r['reference_id'].encode() in whole for r in refs)
  assert b'Proposed reference' not in whole and b'Standard family:' not in whole
 manifest['files'].append(str(p));key.append({'filename':p.name,'source':src.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'expected_reference_source':str(lib/next(r['file'] for r in refs if r['reference_id']==refid)),'expected_family':'nda' if refid.startswith('NDA') else 'customer_order'})
# Scope unsupported by any of the eight references: reseller cloud request.
src=lib/'incoming-tests/Incoming - Ambiguous Reseller Cloud Scan Purchase.docx'
p=out/(labels[8]+'.docx');docx([u['text'] for u in extract_file(src)['units'] if not u['text'].startswith(('Record:','Proposed reference:'))],p)
manifest['files'].append(str(p));key.append({'filename':p.name,'source':src.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'expected_reference_source':None,'expected_family':'customer_order'})
p=out/(labels[9]+'.docx');docx(['Fictional document for testing','The parties will discuss possible future activities. No product, service or disclosure arrangement is specified.'],p)
manifest['files'].append(str(p));key.append({'filename':p.name,'source':'new context-free negative','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'expected_reference_source':None,'expected_family':None})
(out/'blind-manifest.json').write_text(json.dumps(manifest,indent=2))
(out/'withheld-key.json').write_text(json.dumps(key,indent=2))
pilot={'references':[str(lib/'references/nda/Mutual NDA - Product Evaluation - UK - v0.1.docx'),str(lib/'references/sales-orders/Customer Order - Reseller Desktop Licences - v0.1.docx')], 'files':[str(lib/'incoming-tests'/n) for n in ['Incoming - Evaluation NDA with Longer Retention.docx','Incoming - Desktop Reseller Seat Increase.docx','Incoming - Ambiguous Reseller Cloud Scan Purchase.docx']]}
(out/'pilot-manifest.json').write_text(json.dumps(pilot,indent=2))
print('Prepared manifests and frozen withheld key:',out)
print('key SHA256',hashlib.sha256((out/'withheld-key.json').read_bytes()).hexdigest())
