"""Self-update of the skill from GitHub (for claude.ai, where the skill is uploaded as a zip).

    python3 <skill>/scripts/update.py        → a copy of the skill in a working folder with changed files downloaded;
                                              last line: SKILL_DIR=<folder> — work from it afterwards
    python3 scripts/update.py --release [--note TEXT] [--zip PATH]   — (in the repository) new version.json and zip

The skill's version.json: repository, branch, skill path in it, version number, note and the sha1 of every file. The update
compares it with version.json on GitHub (raw.githubusercontent.com) and downloads only the files whose sha1 differs.
No network / private repository / domain not allowed — work continues with the version from the zip (no error).
Inside a git repository nothing is downloaded: there git pull does the update."""
import sys, os, json, hashlib, shutil, urllib.request, subprocess

HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # skill folder
MANIFEST='version.json'
WORK=os.environ.get('MSGEN_SKILL_DIR') or os.path.join(os.path.expanduser('~'),'multisim-scheme')
RAW='https://raw.githubusercontent.com/%s/refs/heads/%s/%s/%s'   # repository, branch (may contain «/»), skill path, file

def sha1(path):
    return hashlib.sha1(open(path,'rb').read()).hexdigest()

def load(d):
    try: return json.load(open(os.path.join(d,MANIFEST),encoding='utf-8'))
    except (OSError,ValueError): return None

def url(m,rel):
    base=os.environ.get('MSGEN_UPDATE_URL')            # for testing without GitHub: file:// or your own server
    if base: return base.rstrip('/')+'/'+rel
    return RAW%(m['repo'],m['branch'],m['path'],rel)

def fetch(u,timeout=20):
    with urllib.request.urlopen(u,timeout=timeout) as r: return r.read()

def in_git(d):
    try: return subprocess.run(['git','-C',d,'rev-parse','--is-inside-work-tree'],capture_output=True,text=True).stdout.strip()=='true'
    except OSError: return False

def update():
    global WORK
    local=load(HERE)
    if local is None: print('update: no %s in the skill — using this copy'%MANIFEST); return HERE
    if in_git(HERE):
        print('update: the skill is in a git repository — git pull updates it; version %s (%s)'%(local['version'],local['note'])); return HERE
    work=load(WORK)
    if work is None or work.get('version',0)<local['version']:             # first copy, or a newer zip was uploaded
        try:
            if os.path.exists(WORK): shutil.rmtree(WORK)
            shutil.copytree(HERE,WORK,ignore=shutil.ignore_patterns('__pycache__'))
        except OSError:                                                      # home folder is not writable
            import tempfile; WORK=os.path.join(tempfile.gettempdir(),'multisim-scheme')
            if os.path.exists(WORK): shutil.rmtree(WORK)
            shutil.copytree(HERE,WORK,ignore=shutil.ignore_patterns('__pycache__'))
        work=local
    try:
        remote=json.loads(fetch(url(work,MANIFEST)))
        if remote.get('branch',work['branch'])!=work['branch'] or remote.get('repo',work['repo'])!=work['repo']:
            work=dict(work,repo=remote['repo'],branch=remote['branch']); remote=json.loads(fetch(url(work,MANIFEST)))
    except Exception as e:
        print('update unavailable (%s: %s) — using version %s from the zip: %s'%(type(e).__name__,e,work['version'],work['note']))
        print('  (needed: public repository %s and network access to raw.githubusercontent.com in the claude.ai settings)'%work['repo'])
        print('SKILL_DIR='+WORK); return WORK
    changed=[f for f,h in remote['files'].items() if not os.path.exists(os.path.join(WORK,f)) or sha1(os.path.join(WORK,f))!=h]
    gone=[f for f in work.get('files',{}) if f not in remote['files']]
    try:
        for f in changed:
            data=fetch(url(remote,f))
            if hashlib.sha1(data).hexdigest()!=remote['files'][f]: raise ValueError('sha1 mismatch for %s'%f)
            p=os.path.join(WORK,f); os.makedirs(os.path.dirname(p),exist_ok=True); open(p,'wb').write(data)
    except Exception as e:
        print('update interrupted (%s: %s) — using version %s'%(type(e).__name__,e,work['version']))
        print('SKILL_DIR='+WORK); return WORK
    for f in gone:
        p=os.path.join(WORK,f)
        if os.path.exists(p): os.remove(p)
    json.dump(remote,open(os.path.join(WORK,MANIFEST),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    if changed or gone or remote['version']!=work['version']:
        print('skill updated from GitHub: version %s → %s (%d files)'%(work['version'],remote['version'],len(changed)+len(gone)))
        if 'SKILL.md' in changed: print('  SKILL.md changed — read the new one: %s/SKILL.md'%WORK)
    else:
        print('skill is the latest version from GitHub: %s'%remote['version'])
    print('version note: '+remote['note'])
    print('SKILL_DIR='+WORK)
    return WORK

def release(note,zip_path=None):
    """(in the repository) version.json from the skill files in git ls-files; version +1 when the files or the note changed"""
    old=load(HERE) or dict(repo='vovandel155-tech/multisim-schemes',branch='main',
                           path='.claude/skills/multisim-scheme',version=0,note='',files={})
    ls=subprocess.check_output(['git','-C',HERE,'ls-files','-z','.'],text=True).split('\0')
    files={f:sha1(os.path.join(HERE,f)) for f in sorted(ls) if f and f!=MANIFEST and os.path.exists(os.path.join(HERE,f))}
    m=dict(old,files=files)
    if files!=old['files'] or (note and note!=old['note']): m['version']=old['version']+1
    if note: m['note']=note
    json.dump(m,open(os.path.join(HERE,MANIFEST),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    print('version.json: version %s, %d files — %s'%(m['version'],len(files),m['note']))
    if zip_path:
        import zipfile
        with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
            for f in list(files)+[MANIFEST]:
                a='multisim-scheme/'+f; assert a.isascii(),'non-ASCII path: '+a
                z.write(os.path.join(HERE,f),a)
        print('zip: %s (%d files, %d KB)'%(zip_path,len(files)+1,os.path.getsize(zip_path)//1024))

if __name__=='__main__':
    a=sys.argv[1:]
    if a[:1]==['--release']:
        note=a[a.index('--note')+1] if '--note' in a else ''
        release(note,a[a.index('--zip')+1] if '--zip' in a else None)
    else:
        update()
