#!/usr/bin/env python3
"""Reproducible paired DeepSeek evaluation. Never prints API credentials."""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
from pathlib import Path
import random
import time
import urllib.request

SKILL = Path(__file__).resolve().parents[1]
ROOT = SKILL
EVAL = SKILL / 'tests/persona-ab-v1'
OUT = SKILL / '.local-evals' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
BASE = ''
CASES = []

def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf8')

def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()

def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    global OUT, BASE, CASES
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true', help='Make paid API requests; otherwise only freeze inputs.')
    parser.add_argument('--max-tokens', type=int, default=8192)
    parser.add_argument('--pilot-first', action='store_true', help='Require a complete first pair before running remaining cases.')
    parser.add_argument('--resume-failed', action='store_true', help='Retry incomplete arms once, preserving their first attempt.')
    parser.add_argument('--cases-file', type=Path, default=EVAL/'holdout.jsonl', help='Frozen JSONL questions; optional checks are never sent to answerer.')
    parser.add_argument('--base-system-file', type=Path, default=EVAL/'shared-system.txt', help='Shared instruction used verbatim by both arms.')
    parser.add_argument('--context-file', type=Path, default=EVAL/'run/context-snapshot.json', help='Frozen Skill inputs; use --current-skill to evaluate current files.')
    parser.add_argument('--current-skill', action='store_true')
    parser.add_argument('--output', type=Path, default=OUT, help='New output directory; existing frozen inputs will not be overwritten.')
    args = parser.parse_args()
    if args.cases_file:
        custom_cases = [json.loads(line) for line in args.cases_file.read_text().splitlines() if line.strip()]
        CASES = [(r['id'], r['category'], [m['content'] if isinstance(m, dict) else m for m in r['messages']], r.get('checks', [])) for r in custom_cases]
    if args.base_system_file:
        BASE = args.base_system_file.read_text().strip()
    OUT = args.output.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'config.json').exists() and not args.resume_failed:
        raise SystemExit('Refusing to overwrite frozen evaluation. Choose a new release directory in a separate script revision.')
    files = ['SKILL.md', 'references/expression-dna.md'] + ['references/'+p.name for p in sorted((SKILL/'references').glob('*framework.md'))]
    snapshot = ({name:(SKILL/name).read_text() for name in files} if args.current_skill else json.loads(args.context_file.read_text()))
    context = '\n\n'.join(f'### FILE {name}\n{text}' for name,text in snapshot.items())
    checks = [{'id':i,'category':cat,'messages':messages,'checks':c} for i,cat,messages,c in CASES]
    if args.resume_failed:
        previous_config = json.loads((OUT/'config.json').read_text())
        current_questions = ''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in checks)
        if previous_config['files_sha256'] != {n:digest(t) for n,t in snapshot.items()} or previous_config['parameters']['max_tokens'] != args.max_tokens or previous_config['base_system'] != BASE or previous_config['holdout_sha256'] != digest(current_questions):
            raise SystemExit('Frozen context, shared prompt, questions or token budget differs; refusing resume.')
    (OUT/'holdout.jsonl').write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in checks))
    write(OUT/'context-snapshot.json', snapshot)
    config = {'created_at':stamp(),'endpoint':'https://api.deepseek.com/chat/completions','parameters':{'model':'deepseek-flash','reasoning_effort':'low','max_tokens':2200,'stream':False},'base_system':BASE,'files_sha256':{n:digest(t) for n,t in snapshot.items()},'holdout_sha256':digest((OUT/'holdout.jsonl').read_text()),'protocol':'12 cases, 3 two-turn cases; same fixed user followups; no expected checks sent to answerer; no external tools; same parameters and shared goal; ON adds snapshot only. max_tokens includes model reasoning where applicable. No retries, two concurrent arms. Blind labels hide arm assignment but cannot hide style.','python_random_seed':741932,'run_requested':args.run}
    config['parameters']['max_tokens'] = args.max_tokens
    config['pilot_first'] = args.pilot_first
    config['protocol'] = f'{len(CASES)} cases, {sum(len(c[2]) > 1 for c in CASES)} multi-turn cases; same shared system instruction, fixed user turns and parameters; ON adds frozen context only. Checks never sent to answerer. No tools. At most one explicit failed-arm retry with original preserved. Two concurrent arms. Blind labels hide arm assignment, not style.'
    if args.resume_failed:
        config = previous_config
    else:
        write(OUT/'config.json',config)
    if not args.run:
        print('Frozen input only. No API calls. For a paid run, use --run with a different output directory.')
        return
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        for line in ((ROOT/'.env.local').read_text().splitlines() if (ROOT/'.env.local').exists() else []):
            if line.startswith('DEEPSEEK_API_KEY='):
                key = line.split('=',1)[1].strip().strip('\"\'')
    if not key:
        raise SystemExit('Missing DEEPSEEK_API_KEY; no requests made.')
    rng=random.Random(741932)
    order=[(i,arm) for i in range(len(CASES)) for arm in ('on','off')]
    rng.shuffle(order)
    retained=[]
    if args.resume_failed:
        pending=[]
        for idx,arm in order:
            path=OUT/f'answer-{CASES[idx][0]}-{arm}.json'
            if not path.exists():
                raise SystemExit('Resume requires all first attempts to have finished.')
            result=json.loads(path.read_text())
            if result['complete']:
                retained.append(result)
            else:
                archived=path.with_name(path.stem+'-attempt1.json')
                if archived.exists():
                    raise SystemExit('Only one retry permitted.')
                write(archived,result)
                pending.append((idx,arm))
        order=pending
    def answer(item):
        idx,arm=item
        ident,category,user_turns,_=CASES[idx]
        system=BASE + ('\n\n请采用下面已激活的人物 Skill 与参考资料。\n'+context if arm=='on' else '')
        history=[{'role':'system','content':system}]
        result={'id':ident,'arm':arm,'category':category,'turns':[],'complete':True}
        for user in user_turns:
            history.append({'role':'user','content':user})
            payload={**config['parameters'],'messages':history.copy()}
            start=stamp(); timer=time.monotonic()
            try:
                req=urllib.request.Request(config['endpoint'], data=json.dumps(payload).encode(), headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
                with urllib.request.urlopen(req,timeout=240) as response:
                    body=json.load(response)
                choice=body['choices'][0]
                answer_text=choice['message'].get('content','')
                turn={'started_at':start,'elapsed_seconds':round(time.monotonic()-timer,3),'request':payload,'response':body}
                result['turns'].append(turn)
                history.append({'role':'assistant','content':answer_text})
                if choice.get('finish_reason') != 'stop' or not answer_text:
                    result['complete']=False
            except Exception as exc:
                # Never record credential-bearing request headers or arbitrary error text.
                result['turns'].append({'started_at':start,'elapsed_seconds':round(time.monotonic()-timer,3),'request':payload,'error_type':type(exc).__name__,'http_status':getattr(exc,'code',None)})
                result['complete']=False
                break
        write(OUT/f'answer-{ident}-{arm}.json',result)
        print(ident,arm,'complete' if result['complete'] else 'incomplete',flush=True)
        return result
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results=retained.copy()
        if args.pilot_first and not args.resume_failed:
            results=list(pool.map(answer,[(0,'on'),(0,'off')]))
            if not all(r['complete'] for r in results):
                write(OUT/'run-summary.json', {'status':'pilot_incomplete','arms_complete':sum(r['complete'] for r in results)})
                return
            order=[item for item in order if item[0] != 0]
        results.extend(pool.map(answer,order))
    by_id={(r['id'],r['arm']):r for r in results}
    blind=[]; mapping=[]
    for ident,category,messages,checks in CASES:
        arms=['on','off'];rng.shuffle(arms)
        case={'id':ident,'category':category,'user_turns':messages,'expected_checks':checks,'candidates':{}}
        for label,arm in zip(('X','Y'),arms):
            record=by_id[ident,arm]
            case['candidates'][label]={'complete':record['complete'],'answers':[t.get('response',{}).get('choices',[{'message':{}}])[0]['message'].get('content','') for t in record['turns']]}
            mapping.append({'id':ident,'label':label,'arm':arm})
        blind.append(case)
    (OUT/'blind-package.jsonl').write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in blind))
    write(OUT/'UNBLIND-KEY.json',mapping)
    write(OUT/'run-summary.json',{'completed_at':stamp(),'arms_total':len(results),'arms_complete':sum(r['complete'] for r in results),'requests':sum(len(r['turns']) for r in results),'returned_models':sorted(set(t['response'].get('model','') for r in results for t in r['turns'] if 'response' in t)),'usage':{k:sum(t.get('response',{}).get('usage',{}).get(k,0) for r in results for t in r['turns']) for k in ('prompt_tokens','completion_tokens','total_tokens')}})

if __name__=='__main__':
    main()
