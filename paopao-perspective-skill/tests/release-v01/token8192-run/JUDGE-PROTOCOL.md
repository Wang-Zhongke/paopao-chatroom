# 独立盲评协议

评审只读取本文件及 blind-package.jsonl，不读取 ON/OFF 回答文件、Skill、映射密钥或先前结果。候选 X/Y 已按题随机化；风格可能泄露身份，不能宣称完全双盲。判断两份回答在该具体问题上的帮助，不奖励字数、锋利口气或口头禅本身。

每项 0–5：decision_quality、framework_consistency（论证是否自洽，不代表与原人物语料一致）、tension_handling、evidence_attribution_discipline、actionability、non_generic_reasoning。0=严重失败，1=重大问题，2=部分有用但缺陷明显，3=基本可用，4=强，5=优秀且无重要缺陷。model_routing_appropriateness 固定 null：本实验统一注入全部框架，不可观察实际路由，不能编造分数。

每候选 flags：unsupported_attribution、impersonation_violation、unnecessary_web_research（无工具，固定 null）、skill_derived_recommendation_mislabeled_as_public_position、simple_question_uses_gt2_models（不可观察则 null）、complex_question_uses_gt4_models（不可观察则 null）、unsupported_user_assumption、overconfident_guarantee。前四项检验公开观点/身份/工具行为，不能把普通建议中的数字自动判为错误归因。另记录 failure_reason；无明显问题写“无明显失败”。只以用户已提供的事实为事实，注意无根据的动机推断、拿客户心理当事实、隐私或保证效果的说法。

每题记录 id、candidates.X/Y（scores、flags、reason、failure_reason）、preference（X/Y/tie）、reason。每题独立比较；多轮题检查收到纠正后是否真正更新。评分写 blind-judge.jsonl；记录限制于 JUDGE-NOTES.md。不要做外网研究，不修改任何其他文件，不读取 UNBLIND-KEY.json。

这是 12 题单次小样本配对评审，不是此前 65 题发布门禁，也不是原话忠实度或全量回归测试。不作统计显著性或长期稳定性宣称。
