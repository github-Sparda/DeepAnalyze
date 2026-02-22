# Gate Narrative Baseline

{
  "raw_unknown": {
    "report_v2": 6,
    "report_v8": 0
  },
  "raw_gate_eq": {
    "report_v2": 0,
    "report_v8": 0
  },
  "metric_eq_chain": {
    "report_v2": 238,
    "report_v8": 213
  }
}

## v2 不可读样例
- 据：围绕“Normal 与 EP 组间存在显著差异特征”的关键观测为 定量指标：tested_features=54；显著特征数(p&lt;0.05)=46count（阈值 &gt;=1）；top_features=['peak5', 'peak29', 'peak28', 'peak23', 'peak49']；显著特征数(q&lt;0.05)=46count（阈值 &gt;=1）。；关键特征来源：result/top_fea
- tures.json。。关键数值与阈值判定如下：tested_features=54，阈值未定义，判定=unknown，方向解释=unknown；显著特征数(p&lt;0.05)=46count，阈值 &gt;=1，判定=pass（46 &gt;= 1），方向解释=数值越高支持越强；top_features=['peak5', 'peak29', 'peak28', 'peak23', 'peak
- <div class="chart-explain"><p><strong>假设</strong>：H1: 差异检验。</p><p><strong>验证</strong>：按 p/q 值排序，展示 Top 特征。</p><p><strong>坐标</strong>：Y 为特征名；X 轴取决于绘图实现（通常为显著性或效应相关指标）。请结合 t
- 量约 46 个（上调 13，下调 33）；代表性特征：peak5（未知语义） (mean_diff=-0.0479, p=0)、peak29（未知语义） (mean_diff=0.906, p=0)、peak28（未知语义） (mean_diff=0.12, p=0)。</p><p><strong>后续</strong>：建议对 Top 特征进行效应量复核与独立验证，并结合生物学/业务背景解释方向性。</p></di
- 依据：围绕“关键指标组合可作为 EP 的有效诊断标志物”的关键观测为 定量指标：majority_accuracy=0.6320807627593943；质心分类准确率=0.0ratio（阈值 &gt;=0.6）；交叉验证平均准确率=0.7150779701749508ratio（阈值 &gt;=0.6）；cv_std_accuracy=0.013766579422172203。；效应量证据：majority_accuracy=0.
- 6320807627593943；centroid_accuracy=0.0；cv_mean_accuracy=0.7150779701749508；cv_std_accuracy=0.013766579422172203。。关键数值与阈值判定如下：majority_accuracy=0.6320807627593943，阈值未定义，判定=unknown，方向解释=unknown；质心分类准确率=0.0ratio，阈值 &gt;
- 判定=pass（0.7151 &gt;= 0.6），方向解释=数值越高支持越强；cv_std_accuracy=0.013766579422172203，阈值未定义，判定=unknown，方向解释=unknown。门槛类型=predictive_performance，门槛状态=partial，未通过检查=path_consistency,primary_performance_ge_min，原因码=method_conflic
- <p>依据：围绕“EP 样本存在潜在的生物学亚型”的关键观测为 定量指标：strongest_pair=['peak10', 'peak17']；最强绝对相关系数=0.975123349389409corr（阈值 &gt;=0.5）；|corr|&gt;0.7 边数=40count（阈值 &gt;=1）；abs_corr_gt_0_5_edges=129。；效应量证据：strongest_abs_corr=0.97512