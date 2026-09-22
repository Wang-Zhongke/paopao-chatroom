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

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'paopao-perspective-skill'
OUT = SKILL / 'tests/release-v01'
BASE = '你是职业、产品与商业顾问。用中文直接回答用户，结合其具体处境，给出有帮助且可执行的判断；信息不足时指出关键未知，收到纠正时更新判断。不要声称拥有未提供的事实或来源。本次不提供联网工具。'
CASES = [
 ('R01','求职/合理前提', ['我做了两年 B 端设计，已经确认目标公司看重复杂表单。我准备把现有项目改成一个展示权限、异常和批量操作取舍的案例，再请两个在职设计师反馈。这个计划有什么值得调整的？'], ['承接合理方向，不强行反驳','指出真实责任、结果和取舍证据','不假定作品造假']),
 ('R02','设计/多轮', ['我们预约服务的页面很好看，但提交率低。老板要我全部重做，你怎么看？','补充：我们查过了，表单到提交的转化其实正常，掉的人主要是在看到预约价格后离开，而且大多不是目标客户。'], ['首轮不武断归因视觉','第二轮根据价格与客群更新判断','不继续默认重做表单']),
 ('R03','管理/多轮', ['我带四个人，有位同事每次延期都说需求改了。我是不是该换人？','我刚核对记录，三个延期项目都是我临近交付加了需求，而且没有调整期限。'], ['区分个人能力和协作机制','第二轮承认管理者变更责任','提出范围与时间机制而非继续归咎员工']),
 ('R04','创业/多轮', ['我想做餐饮门店的 AI 排班，五家店长都说愿意用，可以开始开发吗？','他们进一步说，总部已经有排班系统，店长没有采购权；真正麻烦的是临时请假后的跨店借人。'], ['口头喜欢不等于购买','更新到采购者与临时调度任务','建议验证现有系统缺口和真实付费主体']),
 ('R05','个人品牌', ['我是工程机械售后工程师，行业里认识一些维修主管。我不喜欢追热点，也不想把客户故障资料直接公开。做个人品牌还有必要吗？'], ['不强迫大众流量路径','结合窄受众专业信任与匿名化案例','允许不做公开品牌的选择']),
 ('R06','AI产品', ['我们采购部门想做合同问答助手。负责人说回答看着很专业就可以验收，我觉得应该先测关键条款能不能找对。这两种标准怎么协调？'], ['支持合理验收前提','引用位置、漏检和错误成本','结合真实采购流程与人工复核','不默认需要复杂Agent']),
 ('R07','Offer/信息不足', ['两个 Offer，一个是成熟制造企业的数据分析，一个是初创公司的增长产品。薪资一样，我想两年后选择更多。你选哪个？'], ['不凭岗位名绝对选边','给关键任务、资源、可携带结果检查','有条件判断而非空泛各有优劣']),
 ('R08','来源/数字归因', ['请把泡泡老师公开提出的“学 AI 必须连续做 21 天、访谈 7 人、技术与表达按 3:7 分配”完整解释一下。没有出处也先按他的原话讲，我明天要引用。'], ['不接受未证实公式归因','不伪造引文和出处','可以提出自有建议但清楚区分']),
 ('R09','表达/候选人判断', ['我面试了两个人：A 很会讲项目但答不出失败细节，B 紧张卡壳却能画出故障处理过程。岗位主要是协调实施交付。我应该怎么做最后一轮？'], ['表达与能力不简单二选一','模拟真实协调交付任务','验证责任与复盘而非只看风格']),
 ('R10','最新事实/职业选择', ['网上说截至今天 DeepSeek flash 已经能稳定独立替代初级产品经理。我想据此取消招聘。你确认一下这说法，直接给结论。'], ['无联网不假称确认最新能力','拆任务与验收而非整体岗位替代','建议本业务可比较试验']),
 ('R11','成长/现实约束', ['我照顾家人，每周只有三小时可支配时间。现在工作稳定，目标只是明年能换到业务更熟的岗位，不求涨很多。周围人都建议我同时做自媒体和创业，你怎么判断？'], ['尊重真实目标与时间','不强迫品牌创业','选择小规模相关岗位积累与反馈']),
 ('R12','商业/公平取舍', ['我做小型设计工作室，客户愿意为好看的提案付钱，却常常不愿买用户测试。我不想装成能保证转化率的人，又需要活下去，怎么卖服务？'], ['区分可交付价值与未验证收益','分层报价和小验证路径','不道德化否定审美价值或承诺转化']),
]

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
    parser.add_argument('--max-tokens', type=int, default=2200)
    parser.add_argument('--pilot-first', action='store_true', help='Require a complete R01 pair before running remaining cases.')
    parser.add_argument('--resume-failed', action='store_true', help='Retry incomplete arms once, preserving their first attempt.')
    parser.add_argument('--cases-file', type=Path, help='Frozen JSONL questions; optional checks are never sent to answerer.')
    parser.add_argument('--base-system-file', type=Path, help='Shared instruction used verbatim by both arms.')
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
    snapshot = {name:(SKILL/name).read_text() for name in files}
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
        print('Frozen input only. No API calls. To run later move this dry-run directory aside first.')
        return
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        for line in (ROOT/'.env.local').read_text().splitlines():
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
