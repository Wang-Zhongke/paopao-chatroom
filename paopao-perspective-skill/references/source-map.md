# Source Map

调研截止：2026-09-13。身份对象仅限李泽同（像素范儿创始人；公开名水球泡/水球泡77；常称泡泡老师）。完整身份排除规则见 [research/00-identity-and-source-policy.md](research/00-identity-and-source-policy.md)。

## 读法

- **A**：本人/像素范官方的完整视频、直播或本人节目。
- **B**：完整访谈或保留上下文的授权直播切片。
- **C**：像素范官方历史课程、公开演讲、本人著作/团队课程。
- **D**：本人公开社交媒体正文；适合确认当期判断，不单独证明长期观点。
- **E**：第三方报道、评论与争议材料；只作背景或交叉验证。
- **V3-M**：有带时间轴的可检索机器文本，其中 `ai-zh` 是 Bilibili 机器字幕，`OCR` 是画面烧录字幕识别；可用于定位和语义分析，但不等于人工校正逐字稿。
- **V2**：有完整正文/Show Notes/可读摘要；**V1**：只能确认标题、简介和元数据。

本轮研究除早期课程、文章、播客和社交媒体来源外，已对 Bilibili 官方账号「像素范」（MID `15741969`）的「泡言泡语」系列（series_id `1210820`）建立全量本地研究语料：353 条视频，覆盖 2021-05-26 至 2026-09-08，总时长约 121.89 小时；其中 154 条取得 Bilibili `ai-zh` 机器字幕，199 条由画面烧录字幕 OCR 获得文本。353 条均有可检索机器文本，但未经逐字人工校正；引用前仍须回看时间轴和画面。本 Skill 不把标题、简介、Show Notes 或机器误识别冒充本人原话。

## 核心来源

| ID | 日期 | 来源 | 等级/可读性 | 主要用途 | 不可支持 |
|---|---:|---|---|---|---|
| S00 | 2021-05-26—2026-09-08 | [官方「泡言泡语」系列](https://space.bilibili.com/15741969/channel/seriesdetail?sid=1210820)；[本地语料说明](sources/bilibili/README.md)；[质量审计](sources/bilibili/transcript-qa.md) | A · V3-M（353/353；154 `ai-zh`、199 画面 OCR） | 跨时期检索职业、AI、求职、个人成长、个人品牌、商业管理、设计/产品与表达方式；校验观点是否跨视频、跨时间复现 | 人工逐字稿精度；未回看画面的精确引语；由单条视频直接推定长期稳定观点 |
| S01 | 2015 | [早期 UI 公开课](https://www.bilibili.com/video/BV1xs411d7C3/) | C/E · V1 | 身份与早期技法教学 | 长期职业观 |
| S02 | 2016 | [经济观察网：培训机构为什么做产品](https://www.eeo.com.cn/2016/1214/295129.shtml) | E（含本人引语）· V2 | 社群、产品、真实项目、课程迭代 | 学员结果与个人全部决策 |
| S03 | 2020（回顾早期实践） | [《像素的艺术》公开试读](https://s.zhangyue.com/read?anchorId=&appId=8a7ff2af&bid=12331541&cid=4&rentId=106910) | C · V2 | 思想/技法/软件层级、作业反馈 | 2026 职业判断；团队署名不能逐句归于本人 |
| S04 | 2017 | [UI 设计新思维课程摘要](https://www.zcool.com.cn/article/ZNDg3ODY4.html) | C/B · V2 | 市场、学习与设计议题 | 摘要中问题的完整答案 |
| S05 | 2017 | [官方 Sketch 教程](https://www.bilibili.com/video/BV14x411Y7sa/) | A/C · V1 | 工具教学时期锚点 | “只重工具” |
| S06 | 2018 | [UI 入行三个新观点](https://www.sohu.com/a/241512898_100148435) | C/B · V2 | 工具短寿命、需求侧定价、岗位分化 | 所有行业的普遍规律 |
| S07 | 2021 | [高薪设计师面试](https://www.bilibili.com/video/BV12o4y1X7GS/) | A · V3-M | 就业与表达主题 | 具体面试评分表 |
| S08 | 2021 | [UI 改版与多场景产品思维](https://www.bilibili.com/video/BV19U4y177aU/) | A · V3-M | 设计与产品连接 | 完整方法论细节 |
| S09 | 2024 | [四次被百度拒绝](https://www.bilibili.com/video/BV1Ai421U7mS/) | A · V3-M | 求职韧性与轨迹非线性 | “被拒就应创业” |
| S10 | 2024 | [B 端就业环境更新](https://www.bilibili.com/video/BV1Ey411z7Xz/) | A · V3-M | 职业建议需带市场版本 | 早期建议为何失效的单一因果 |
| S11 | 2024 | [公司、求职、AI 与职业规划](https://www.bilibili.com/video/BV1p3S8YQEe6/) | A · V3-M | 跨主题长内容锚点 | 未核画面时的精确逐句立场 |
| S12 | 2024 | [混乱公司与靠近交易](https://www.bilibili.com/video/BV1TPBqYnEYK/) | A · V3-M | 真实生产环境、靠近收入 | 高压/混乱一定有利 |
| S13 | 2025 | [设计师转 AI 产品经理](https://www.bilibili.com/video/BV1QXEXzaEvi/) | A · V3-M | 岗位融合与前沿环境 | 所有设计师的必然路径 |
| S14 | 2025 | [老板与员工的不同支点](https://www.bilibili.com/video/BV1soj1zfEWA/) | A · V3-M | 组织动机张力 | 劳资责任对等 |
| S15 | 2025 | [泡泡玛特与非理性需求](https://www.bilibili.com/video/BV1m9KBzHEVQ/) | A · V3-M | 用户需求与商业价值 | 单案例的普适产品规律 |
| S16 | 2025 | [工作、供需与压力成长](https://www.bilibili.com/video/BV1rg37zfE3a/) | A · V3-M | 交换关系与环境密度 | 伤害性加班合理化 |
| S17 | 2025 | [跳槽前的“存档点”](https://www.bilibili.com/video/BV1DWJ9zNEWh/) | A · V3-M | 可携带项目/管理资产 | 紧急退出时仍应等待 |
| S18 | 2025 | [制度、规则与激励这个“第三者”](https://www.bilibili.com/video/BV1W7HWzyECz/) | A · V3-M | 隐藏规则/激励结构 | 具体劳动法事实 |
| S19 | 2025 | [105 分钟完整访谈](https://www.xiaoyuzhoufm.com/episode/695310e64f0ee6344823d5ed) | B · V2 | 标准执行压缩、一人公司、数据/信任/审美/影响力 | Show Notes 外的逐字表述 |
| S20 | 2026 | [一人公司先是一门生意](https://www.xiaoyuzhoufm.com/episode/69d0f173b977fb2c4717eb7d) | A · V2 | AI 降本增效须接真实成本 | 未验证的商业模式 |
| S21 | 2026 | [AI+心理/养老 MVP](https://www.xiaoyuzhoufm.com/episode/698b55d8a22480add69121f8) | A · V2 | 具体人/场景/付费、用户共创 | 对所有创业项目的完整方法 |
| S22 | 2026 | [个人品牌替代部分门店位置价值](https://www.bilibili.com/video/BV14GA6zEE1f/) | A · V3-M | 被看见与本地生意分发 | 内容可以替代产品质量 |
| S23 | 2026 | [方向来自行动](https://www.bilibili.com/video/BV1fRAaz1E2C/) | A · V3-M | 生存约束、行动生成信息 | 忽略资源/健康限制 |
| S24 | 2026 | [传统岗位入口叠加 AI 能力](https://www.bilibili.com/video/BV1BJdpBPE9n/) | A · V3-M | 业务翻译与组合型岗位 | 标题式薪资承诺 |
| S25 | 2026 | [自媒体黑箱与连续试验](https://jingxuan.douyin.com/m/video/7621894186496757043) | D · V2 | 低成本发布、适配测试 | 确定收益 |
| S26 | 2026 | [向上管理是价值交换与边界](https://jingxuan.douyin.com/m/video/7622994445843189018) | D · V2 | 先明确技能/资源/平台目标 | 权力不对称与法律边界的完整处理 |
| S27 | 2026 | [垂类数据、意图、评测与 AI 落地](https://jingxuan.douyin.com/m/video/7630349917109734682) | D · V2 | 岗位迁移、业务落地 | 净就业数量预测 |
| S28 | 2026 | [耐久能力：英语、身体、持续学习、实践](https://jingxuan.douyin.com/m/video/7655598829928058118) | D · V2 | 跨周期积累 | 具体专业选择的替代方案 |
| S29 | 2026 | [长期更新、流量与个人品牌](https://www.bilibili.com/video/BV1TBuG6MEpS/) | A · V3-M | 个人品牌第二资产 | “发就一定成功” |
| S30 | 2026 | [直接连接市场与跨风口流量](https://jingxuan.douyin.com/m/video/7681621261541330202) | D · V2 | 直接市场反馈 | 基础研究与组织内创新无价值 |
| S31 | 2026 | [AI 工具不等于内容能力](https://jingxuan.douyin.com/m/video/7683404208472624434) | D · V2 | 工具起点被抹平，内容/信任仍分化 | “被喜欢”替代专业与伦理 |

## 外部校正来源

| ID | 来源 | 用途 |
|---|---|---|
| X01 | [绿色中国人物报道](https://www.greenchina.tv/magazine/detail/id/2753.html) | 教育、工作、创办像素范儿的背景；后发人物稿，不作核心观点唯一证据 |
| X02 | [站酷高高手讲师档案](https://www.gogoup.com/teacher/38) | 李泽同—水球泡—像素范身份链与职业经历 |
| X03 | [MindStore/爱范儿：优阁与像素范儿](https://www.ifanr.com/704718) | 联合创始人视角，校正“单人天才叙事” |
| X04 | [石家庄像素范儿课程与就业销售页面](https://www.pxfer.com/) | 识别商业利益冲突；不能验证课程结果 |
| X05 | [第三方争议评论](https://bin.zmide.com/?p=646) | 证明争议与品牌身份关联；不裁定事实真伪 |

## Coverage gaps

1. 353 条官方视频均已有机器文本，但 `ai-zh` 与画面 OCR 都不是逐字人工校正稿；精确引用、反讽、说话者切换、画中外部素材和关键数字必须回看原视频。
2. [`BV13oMn6PEKH`](https://www.bilibili.com/video/BV13oMn6PEKH/) 已从 4:35 试看 OCR 缺口恢复为 1640 段 `ai-zh`；视频夹有多段第三方材料，必须按证据卡分离归因，欺骗性招聘做法只作为反模式。
3. [`BV1RJ4m1p7vc`](https://www.bilibili.com/video/BV1RJ4m1p7vc/) 已通过 270 段 `ai-zh` 与 282 段正确裁区 OCR 交叉核验，升级为 `reviewed-usable`；案例数字、排他性筛选与精确引语仍须谨慎。
4. 当前 353 条均无 `coverage-gap` 或 `unusable`，但机器文本让全系列可检索不等于自动提高命题置信度。每个关键 Mental Model 仍须至少两条独立公开视频支持，优先跨时间或跨场景复现，并区分长期稳定观点与一次直播的临场判断。
5. 背调、谈薪、简历筛选、面试评分和内部招聘逻辑仍缺少两份独立、完整上下文的一手材料。
6. 内部团队管理、绩效、解雇、股权分配和知识付费经营数据没有可审计的一手记录。
7. 学员长期就业、收入和退费结果没有独立统计，培训成功案例存在选择偏差。
8. 2026 年的 AI 岗位与赛道判断高度时效；使用时必须重新查市场、JD、薪资和政策。

完整检索记录、排除项和各维度证据见 [research/](research)。
